import threading
import time
import json
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from settings import load_settings

from components.ds1 import run_ds1
from components.dus1 import run_dus1
from components.dpir1 import run_dpir1
from components.four_sd import run_four_sd
from components.btn import run_btn
from components.dht import run_dht
from components.gyro import run_gyro

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

HOSTNAME = "localhost" 
PORT = 1883
batch = []
counter_lock = threading.Lock()
publish_data_limit = 5
publish_data_counter = 0
publish_event = threading.Event()

four_sd_device = None

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
        batch.append((topic, json.dumps(payload), 0, False))
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
        try:
            publish.multiple(local_batch, hostname=HOSTNAME, port=PORT)
            print(f"[PI2 MQTT] Poslato {len(local_batch)} poruka.")
        except Exception as e:
            print(f"[PI2 MQTT ERROR] Neuspesno slanje: {e}")

        # Resetujemo event da bismo mogli ponovo da cekamo
        event.clear()

def ds2_callback(val): 
    add_to_batch("Sensors/DS2", 
                 create_payload(settings['DS2'], "Door_Status", val))
    print(f"[DS2] Status: {val}")

def btn_callback(val): 
    add_to_batch("Sensors/BTN", 
                 create_payload(settings['BTN'], "Button_Pressed", val))
    print(f"[BTN] Pressed: {val}")

def dus2_callback(distance): 
    add_to_batch("Sensors/DUS2", 
                 create_payload(settings['DUS2'], "Distance", distance))
    print(f"[DUS2] Dist: {distance:.2f} cm")

def dpir2_callback(): 
    add_to_batch("Sensors/DPIR2", 
                 create_payload(settings['DPIR2'], "Motion", 1))
    print(f"[DPIR2] Motion Detected")

def dht_callback(humidity, temperature, event, cfg):
    # Slanje vlaznosti
    if humidity is None or temperature is None:
        return
    
    add_to_batch("Sensors/DHT", 
                 create_payload(cfg, "Humidity", humidity))
    # Slanje temperature
    add_to_batch("Sensors/DHT", 
                 create_payload(cfg, "Temperature", temperature))
    print(f"[{cfg['name']}] Temp: {temperature:.1f}C, Hum: {humidity:.1f}%")

def gyro_callback(accel, rotation, event, cfg):
    # Accel i Rotation su liste [x, y, z]
    add_to_batch("Sensors/Gyro", 
                 create_payload(cfg, "Acceleration", str(accel)))
    add_to_batch("Sensors/Gyro", 
                 create_payload(cfg, "Rotation", str(rotation)))
    # print(f"[{sensor_settings['name']}] Data sent") #da ne bi spamovalo

def on_connect(client, userdata, flags, rc):
    client.subscribe("Commands/PI2/#")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get("command")
        
        if msg.topic == "Commands/PI2/4SD":
            if command == "show":
                text = payload.get("text", "00:00")
                if four_sd_device:
                    four_sd_device.display_text(text)
            elif command == "blink":
                if four_sd_device:
                    four_sd_device.blink("00:00")
            elif command == "clear":
                if four_sd_device:
                    four_sd_device.clear()
            
    except Exception as e:
        print(f"Error handling MQTT command: {e}")

if __name__ == "__main__":
    print('Starting PI2...')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(HOSTNAME, PORT, 60)
    mqtt_client.loop_start()

    # pblisher thread (Daemon)
    pub_thread = threading.Thread(target=publisher_task, args=(publish_event, batch, stop_event))
    pub_thread.daemon = True # Ovo znaci da ce se ugasiti kad se ugasi glavni program
    pub_thread.start()
    threads.append(pub_thread)

    four_sd_device = run_four_sd(settings['4SD'], threads, stop_event, None)
    run_ds1(settings['DS2'], threads, stop_event, ds2_callback)
    run_dus1(settings['DUS2'], threads, stop_event, dus2_callback)
    run_dpir1(settings['DPIR2'], threads, stop_event, dpir2_callback)
    run_btn(settings['BTN'], threads, stop_event, btn_callback)
    run_dht(settings['DHT3'], threads, stop_event, dht_callback)
    run_gyro(settings['GSG'], threads, stop_event, gyro_callback)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping PI2...')
        stop_event.set()
    finally:
        for t in threads:
            t.join()

        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("PI2 stopped.")