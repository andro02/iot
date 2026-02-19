import threading
import time
import sys
import json
import paho.mqtt.publish as publish
from settings import load_settings

# Importi komponenti
from components.ds1 import run_ds1
from components.dms import run_dms
from components.dus1 import run_dus1
from components.dpir1 import run_dpir1
from components.dl import run_dl
from components.db import run_db

# NOVI IMPORTI ZA PI2 i PI3
from components.four_sd import run_four_sd
from components.btn import run_btn     # Koristi logiku DS1
from components.dht import run_dht
from components.gyro import run_gyro
from components.bir import run_bir
from components.brgb import run_brgb
from components.lcd import run_lcd

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

# --- PODESAVANJA MREZE ---
# Promeni na IP svog laptopa ako pokreces sa PI uredjaja
HOSTNAME = "localhost" 
PORT = 1883

# --- GLOBALNE PROMENLJIVE ---
batch = []
counter_lock = threading.Lock()
publish_data_limit = 5
publish_data_counter = 0

# --- POMOCNE FUNKCIJE ---

def create_payload(sensor_settings, measurement, value):
    """ Kreira JSON paket. Value ne konvertujemo u float na silu, 
        ostavljamo da server odluci (zbog stringova kao 'A', 'B'...) """
    return {
        "measurement": measurement,
        "value": value,
        "simulated": sensor_settings['simulated'],
        "runs_on": sensor_settings['runs_on'],
        "name": sensor_settings['name']
    }

def add_to_batch(topic, payload):
    """ Dodaje payload u batch listu i proverava limit """
    global publish_data_counter
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        publish_data_counter += 1
    
    # Ako predjemo limit, saljemo signal publisher thread-u
    if publish_data_counter >= publish_data_limit:
        publish_event.set()

def publisher_task(event, batch_data, stop_event):
    """
    Ovo je DAEMON nit. Ona radi u pozadini i salje podatke na MQTT.
    Salje ako se nakupi dovoljno podataka (publish_data_limit) ILI ako prodje vreme.
    """
    global publish_data_counter
    while not stop_event.is_set():
        event.wait(timeout=5)
        # Cekamo da se napuni lista ili 5 sekundi (timeout)

        # Uzimamo katanac pre nego sto diramo deljenu listu
        with counter_lock:
            if not batch_data:
                continue

            local_batch = batch_data.copy() # Kopiramo podatke da ih posaljemo
            batch_data.clear() # Praznimo glavnu listu
            publish_data_counter = 0 # Resetujemo brojac
            
        # Slanje na MQTT (ovo radimo VAN lock-a da ne blokiramo senzore dok saljemo)
        try:
            publish.multiple(local_batch, hostname=HOSTNAME, port=PORT)
            print(f"\n[MQTT] Poslato {len(local_batch)} vrednosti u batch-u.\n")
        except Exception as e:
            print(f"[MQTT ERROR] Neuspesno slanje: {e}")
        
        # Resetujemo event da bismo mogli ponovo da cekamo
        event.clear()

# Event koji signalizira da je batch pun
publish_event = threading.Event()

# --- CALLBACKS (Specificni za stare komponente koje vracaju samo vrednost) ---

def ds1_callback(val):
    # Logika za senzor vrata
    cfg = settings['DS1']
    payload = create_payload(cfg, "Door_Status", val) # 1 ili 0
    add_to_batch("Sensors/DS1", payload)
    print(f"[DS1] Status: {val}")

def ds2_callback(val):
    cfg = settings['DS2']
    payload = create_payload(cfg, "Door_Status", val)
    add_to_batch("Sensors/DS2", payload)
    print(f"[DS2] Status: {val}")

def btn_callback(val):
    cfg = settings['BTN']
    # Dugme je isto sto i senzor vrata, samo druga namena
    payload = create_payload(cfg, "Button_Pressed", val)
    add_to_batch("Sensors/BTN", payload)
    print(f"[BTN] Pressed: {val}")

def dms_callback(key):
    cfg = settings['DMS']
    payload = create_payload(cfg, "Key_Pressed", key)
    add_to_batch("Sensors/DMS", payload)
    print(f"[DMS] Key: {key}")

def dus1_callback(distance):
    # Ultrazvucni senzor meri distancu
    cfg = settings['DUS1']
    payload = create_payload(cfg, "Distance", distance)
    add_to_batch("Sensors/DUS1", payload)
    print(f"[DUS1] Dist: {distance:.2f} cm")

def dus2_callback(distance):
    cfg = settings['DUS2']
    payload = create_payload(cfg, "Distance", distance)
    add_to_batch("Sensors/DUS2", payload)
    print(f"[DUS2] Dist: {distance:.2f} cm")

# Senzor pokreta detektuje pokret (uvek salje 1 kad detektuje)
def dpir1_callback():
    cfg = settings['DPIR1']
    payload = create_payload(cfg, "Motion", 1)
    add_to_batch("Sensors/DPIR1", payload)
    print(f"[DPIR1] Motion Detected")

def dpir2_callback():
    cfg = settings['DPIR2']
    payload = create_payload(cfg, "Motion", 1)
    add_to_batch("Sensors/DPIR2", payload)
    print(f"[DPIR2] Motion Detected")

def dpir3_callback():
    cfg = settings['DPIR3']
    payload = create_payload(cfg, "Motion", 1)
    add_to_batch("Sensors/DPIR3", payload)
    print(f"[DPIR3] Motion Detected")

# --- CALLBACKS (za komponente koje vracaju i settings) ---

def dht_callback(humidity, temperature, event, sensor_settings):
    # Ovaj callback radi za DHT1, DHT2 i DHT3
    p_hum = create_payload(sensor_settings, "Humidity", humidity)
    p_temp = create_payload(sensor_settings, "Temperature", temperature)
    
    # Slanje vlaznosti
    add_to_batch("Sensors/DHT", p_hum)
    # Slanje temperature
    add_to_batch("Sensors/DHT", p_temp)
    
    print(f"[{sensor_settings['name']}] Temp: {temperature:.1f}C, Hum: {humidity:.1f}%")

def gyro_callback(accel, rotation, event, sensor_settings):
    # Accel i Rotation su liste [x, y, z]
    p_acc = create_payload(sensor_settings, "Acceleration", str(accel))
    p_rot = create_payload(sensor_settings, "Rotation", str(rotation))
    
    add_to_batch("Sensors/Gyro", p_acc)
    add_to_batch("Sensors/Gyro", p_rot)
    # print(f"[{sensor_settings['name']}] Data sent") #da ne bi spamovalo

def bir_callback(key, event, sensor_settings):
    payload = create_payload(sensor_settings, "BIR_Remote", key)
    add_to_batch("Sensors/BIR", payload)
    print(f"[{sensor_settings['name']}] Button: {key}")

# --- CALLBACKS ZA AKTUATORE (Samo za logovanje statusa) ---

def dl_callback(state):
    cfg = settings['DL']
    payload = create_payload(cfg, "Light_Status", 1 if state else 0)
    add_to_batch("Actuators/DL", payload)
    print(f"[DL] Light: {'ON' if state else 'OFF'}")

def db_callback(state):
    cfg = settings['DB']
    payload = create_payload(cfg, "Buzzer_Status", 1 if state else 0)
    add_to_batch("Actuators/DB", payload)
    print(f"[DB] Buzzer: {'ON' if state else 'OFF'}")

def brgb_callback(color):
    cfg = settings['BRGB']
    payload = create_payload(cfg, "RGB_Color", color)
    add_to_batch("Actuators/BRGB", payload)
    print(f"[BRGB] Color: {color}")

def lcd_callback(text):
    # ovo koristimo ako zelimo da posaljemo sta pise na LCD-u
    cfg = settings['LCD']
    payload = create_payload(cfg, "LCD_Text", text)
    add_to_batch("Actuators/LCD", payload)
    print(f"[LCD] Text: {text}")

def input_thread(dl_dev, db_dev, rgb_dev, lcd_dev, stop_event):
    dl_on = False
    db_on = False
    
    print("\n---- KOMANDE ----")
    print("'l': Toggle Light (DL)")
    print("'b': Toggle Buzzer (DB)")
    print("'r': RGB Red")
    print("'g': RGB Green")
    print("'v': RGB Blue") # v kao Violet/Blue
    print("'w': RGB White")
    print("'o': RGB Off")
    print("'t': LCD Test Message")
    print("'x': Exit")
    print("-----------------")

    while not stop_event.is_set():
        try:
            # sys.stdin.readline ne blokira ostale threadove kao input()
            # ali za jednostavnost ovde koristimo input u threadu
            key = input().strip().lower()
            
            if key == 'x':
                stop_event.set()
                break
            
            elif key == 'l':
                dl_on = not dl_on
                dl_callback(dl_on)
                if dl_dev: dl_dev.turn_on() if dl_on else dl_dev.turn_off()
            
            elif key == 'b':
                db_on = not db_on
                db_callback(db_on)
                if db_dev: db_dev.turn_on() if db_on else db_dev.turn_off()
                
            # komande za RGB (PI3)
            elif key in ['r', 'g', 'v', 'w', 'o']:
                color_map = {'r': 'red', 'g': 'green', 'v': 'blue', 'w': 'white', 'o': 'off'}
                color = color_map[key]
                brgb_callback(color)
                if rgb_dev:
                    if color == 'off': rgb_dev.turnOff()
                    else: rgb_dev.set_color(color)

            # text za LCD (PI3)
            elif key == 't':
                msg = "Hello World"
                lcd_callback(msg)
                if lcd_dev: lcd_dev.print_text(msg)

            else:
                print(f"Nepoznata komanda: {key}")
                
        except (KeyboardInterrupt, EOFError):
            print("\nStopping via Ctrl+C")
            stop_event.set()
            break

if __name__ == "__main__":
    print('Starting app')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    # pblisher thread (Daemon)
    pub_thread = threading.Thread(target=publisher_task, args=(publish_event, batch, stop_event))
    pub_thread.daemon = True # Ovo znaci da ce se ugasiti kad se ugasi glavni program
    pub_thread.start()
    threads.append(pub_thread)
    print("Publisher thread started.")

    # inicijalizacija aktuatora (ako nisu simulirani, dobijamo objekte)
    dl_device = run_dl(settings['DL'], threads, stop_event, dl_callback)
    db_device = run_db(settings['DB'], threads, stop_event, db_callback)
    
    # PI2 aktuatori
    # 4SD se vrti sam, ne treba nam kontrola iz konzole, samo ga pokrecemo
    run_four_sd(settings['4SD'], threads, stop_event, None)
    
    # PI3 aktuatori
    rgb_device = run_brgb(settings['BRGB'], threads, stop_event, brgb_callback)
    lcd_device = run_lcd(settings['LCD'], threads, stop_event, lcd_callback)

    # Pokretanje senzora (PI1, PI2, PI3)
    try:
        # PI1
        run_ds1(settings['DS1'], threads, stop_event, ds1_callback)
        run_dms(settings['DMS'], threads, stop_event, dms_callback)
        run_dus1(settings['DUS1'], threads, stop_event, dus1_callback)
        run_dpir1(settings['DPIR1'], threads, stop_event, dpir1_callback)
        
        # PI2
        run_ds1(settings['DS2'], threads, stop_event, ds2_callback) # Koristi run_ds1 logiku
        run_dus1(settings['DUS2'], threads, stop_event, dus2_callback) # Koristi run_dus1 logiku
        run_dpir1(settings['DPIR2'], threads, stop_event, dpir2_callback) # Koristi run_dpir1 logiku
        run_btn(settings['BTN'], threads, stop_event, btn_callback)
        run_dht(settings['DHT3'], threads, stop_event, dht_callback)
        run_gyro(settings['GSG'], threads, stop_event, gyro_callback)
        
        # PI3
        run_dht(settings['DHT1'], threads, stop_event, dht_callback)
        run_dht(settings['DHT2'], threads, stop_event, dht_callback)
        run_bir(settings['IR'], threads, stop_event, bir_callback)
        run_dpir1(settings['DPIR3'], threads, stop_event, dpir3_callback)

        # konzola za input
        input_thread(dl_device, db_device, rgb_device, lcd_device, stop_event)

    except KeyboardInterrupt:
        stop_event.set()
    
    finally:
        for t in threads:
            t.join()
        print("App stopped.")