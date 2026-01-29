import threading
import time
import json
import paho.mqtt.publish as publish
from settings import load_settings

from components.ds1 import run_ds1
from components.dms import run_dms
from components.dus1 import run_dus1
from components.dpir1 import run_dpir1
from components.dl import run_dl
from components.db import run_db

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

# MQTT
HOSTNAME = "localhost"
PORT = 1883

batch = []
# Katanac za thread-safety (da ne bi dva threada pisala u isto vreme)
counter_lock = threading.Lock()
# Koliko podataka skupimo pre nego sto ih posaljemo (ili cekamo tajmer)
publish_data_limit = 5
publish_data_counter = 0

def publisher_task(event, batch_data):
    """
    Ovo je DAEMON nit. Ona radi u pozadini i salje podatke na MQTT.
    Salje ako se nakupi dovoljno podataka (publish_data_limit) ILI ako prodje vreme.
    """
    global publish_data_counter, publish_data_limit
    while True:
        # Cekamo da se napuni lista ili 10 sekundi (timeout)
        event.wait(timeout=10)
        
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

def create_payload(sensor_settings, measurement, value):
    """ Pomocna funkcija za kreiranje JSON payload-a po specifikaciji """
    payload = {
        "measurement": measurement,
        "value": value,
        "simulated": sensor_settings['simulated'],
        "runs_on": sensor_settings['runs_on'],
        "name": sensor_settings['name']
    }
    return payload


# Callbacks
def ds1_callback(val):
    # Logika za senzor vrata
    sensor_config = settings['DS1']
    payload = create_payload(sensor_config, "Door_Status", val) # 1 ili 0
    
    # MQTT Topic: "Senzori/DoorSensor1" (primer)
    topic = "Sensors/DS1"
    
    with counter_lock:
        # Dodajemo u batch u formatu koji paho-mqtt ocekuje: (topic, payload, qos, retain)
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1
    
    # Ako smo napunili batch, budimo publisher thread
    if publish_data_counter >= publish_data_limit:
        publish_event.set()
        
    # Ispis u konzolu za debug (opciono)
    print(f"[DS1] Detected: {val}")

def dms_callback(key):
    sensor_config = settings['DMS']
    payload = create_payload(sensor_config, "Key_Pressed", key)
    topic = "Sensors/DMS"
    
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1
        
    if publish_data_counter >= publish_data_limit:
        publish_event.set()
    
    print(f"[DMS] Key: {key}")

# Senzor pokreta detektuje pokret (uvek salje 1 kad detektuje)
def dpir1_callback():
    sensor_config = settings['DPIR1']
    payload = create_payload(sensor_config, "Motion", 1)
    topic = "Sensors/DPIR1"
    
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1
    
    if publish_data_counter >= publish_data_limit:
        publish_event.set()
        
    print(f"[DPIR1] Motion Detected")

def dus1_callback(distance):
    # Ultrazvucni senzor meri distancu
    sensor_config = settings['DUS1']
    payload = create_payload(sensor_config, "Distance", distance)
    topic = "Sensors/DUS1"
    
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1

    if publish_data_counter >= publish_data_limit:
        publish_event.set()
        
    print(f"[DUS1] Distance: {distance} cm")

def dl_callback(state):
    sensor_config = settings['DL']
    val = 1 if state else 0
    payload = create_payload(sensor_config, "Light_Status", val)
    topic = "Actuators/DL"
    
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1
        
    if publish_data_counter >= publish_data_limit:
        publish_event.set()
        
    status = "ON" if state else "OFF"
    print(f"[DL] Light is {status}")

def db_callback(state):
    sensor_config = settings['DB']
    val = 1 if state else 0
    payload = create_payload(sensor_config, "Buzzer_Status", val)
    topic = "Actuators/DB"
    
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        global publish_data_counter
        publish_data_counter += 1
        
    if publish_data_counter >= publish_data_limit:
        publish_event.set()
        
    status = "BUZZ" if state else "SILENCE"
    print(f"[DB] Buzzer is {status}")

if __name__ == "__main__":
    print('Starting app')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    # Pokretanje Publisher Thread-a (Daemon)
    publisher_thread = threading.Thread(target=publisher_task, args=(publish_event, batch))
    publisher_thread.daemon = True # Ovo znaci da ce se ugasiti kad se ugasi glavni program
    publisher_thread.start()
    threads.append(publisher_thread)
    print("Publisher thread started.")

    try:
        run_ds1(settings['DS1'], threads, stop_event, ds1_callback)
        run_dms(settings['DMS'], threads, stop_event, dms_callback)
        run_dus1(settings['DUS1'], threads, stop_event, dus1_callback)
        run_dpir1(settings['DPIR1'], threads, stop_event, dpir1_callback)

        dl_device = run_dl(settings['DL'], threads, stop_event, dl_callback)
        db_device = run_db(settings['DB'], threads, stop_event, db_callback)
        dl_on = False
        db_on = False

        print("\n---- KOMANDE -----")
        print(" 'l' -> Upali/Ugasi svetlo")
        print(" 'b' -> Upali/Ugasi zujalicu")
        print(" 'x' -> Izlaz")
        print("Svi senzori pokrenuti. Pritisni CTRL+C za izlaz.")
        
        while True:
            command = input("Unesi komandu: ").strip().lower()

            if command == 'l':
                dl_on = not dl_on
                dl_callback(dl_on)
                if not settings['DL']['simulated'] and dl_device:
                    if dl_on: dl_device.turn_on()
                    else: dl_device.turn_off()
            elif command == 'b':
                db_on = not db_on
                db_callback(db_on)
                if not settings['DB']['simulated'] and db_device:
                    if db_on: db_device.turn_on()
                    else: db_device.turn_off()
            elif command == 'x':
                print("Stopping app...")
                stop_event.set()
                break

    except KeyboardInterrupt:
        print('Stopping app')
        stop_event.set()
        for t in threads:
            t.join()