import threading
import time
import sys
import json
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
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

HOSTNAME = "localhost" 
PORT = 1883

batch = []
counter_lock = threading.Lock()
publish_data_limit = 5
publish_data_counter = 0
publish_event = threading.Event()

# Globalni aktuatori da bi im MQTT on_message mogao pristupiti
dl_device = None
db_device = None

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

        # Slanje na MQTT (ovo radimo VAN lock-a da ne blokiramo senzore dok saljemo)
        try:
            publish.multiple(local_batch, hostname=HOSTNAME, port=PORT)
            print(f"[PI1 MQTT] Poslato {len(local_batch)} poruka.")
        except Exception as e:
            print(f"[PI1 MQTT ERROR] {e}")

        # Resetujemo event da bismo mogli ponovo da cekamo
        event.clear()

# --- INPUT THREAD (Za testiranje) ---
# def input_thread(dl_dev, db_dev, stop_event):
#     dl_on = False
#     db_on = False
    
#     print("\n---- KOMANDE (PI1) ----")
#     print("'l': Toggle Light (DL)")
#     print("'b': Toggle Buzzer (DB)")
#     print("'x': Exit")
#     print("-----------------------")

#     while not stop_event.is_set():
#         try:
#             key = input().strip().lower()
            
#             if key == 'x':
#                 stop_event.set()
#                 break
            
#             elif key == 'l':
#                 dl_on = not dl_on
#                 dl_callback(dl_on) # Saljemo podatak i na server
#                 if dl_dev: 
#                     dl_dev.turn_on() if dl_on else dl_dev.turn_off()
            
#             elif key == 'b':
#                 db_on = not db_on
#                 db_callback(db_on) # Saljemo podatak i na server
#                 if db_dev: 
#                     db_dev.turn_on() if db_on else db_dev.turn_off()
#             else:
#                 if key: print(f"Nepoznata komanda: {key}")
                
#         except (KeyboardInterrupt, EOFError):
#             print("\nStopping via Ctrl+C")
#             stop_event.set()
#             break

# --- CALLBACKS ---
def ds1_callback(val): 
    add_to_batch("Sensors/DS1", 
                create_payload(settings['DS1'], "Door_Status", val))
    print(f"[DS1] Status: {val}")

def dms_callback(key): 
    add_to_batch("Sensors/DMS", 
                create_payload(settings['DMS'], "Key_Pressed", key))
    print(f"[DMS] Key: {key}")

def dus1_callback(distance): 
    add_to_batch("Sensors/DUS1",
                create_payload(settings['DUS1'], "Distance", distance))
    # print(f"[DUS1] Dist: {distance:.2f} cm")

def dpir1_callback(): 
    add_to_batch("Sensors/DPIR1",
                create_payload(settings['DPIR1'], "Motion", 1))
    # print(f"[DPIR1] Motion Detected")

def dl_callback(state):
    add_to_batch("Actuators/DL",
                create_payload(settings['DL'], "Light_Status", 1 if state else 0))
    print(f"[DL] Light: {'ON' if state else 'OFF'}")

def db_callback(state):
    add_to_batch("Actuators/DB",
                create_payload(settings['DB'], "Buzzer_Status", 1 if state else 0))
    print(f"[DB] Buzzer: {'ON' if state else 'OFF'}")

# --- SLUSANJE KOMANDI SA SERVERA ---
def on_connect(client, userdata, flags, rc):
    client.subscribe("Commands/PI1/#")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get("command")
        
        if msg.topic == "Commands/PI1/DL":
            if command == "on":
                dl_device.turn_on() if dl_device else None
                dl_callback(True)
            elif command == "off":
                dl_device.turn_off() if dl_device else None
                dl_callback(False)
                
        elif msg.topic == "Commands/PI1/DB":
            if command == "on":
                db_device.turn_on() if db_device else None
                db_callback(True)
            elif command == "off":
                db_device.turn_off() if db_device else None
                db_callback(False)
    except Exception as e:
        print(f"Error handling MQTT command: {e}")

if __name__ == "__main__":
    print('Starting PI1...')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    # Setup MQTT Subscriber
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
    print("Publisher thread started.")

    # inicijalizacija aktuatora (ako nisu simulirani, dobijamo objekte)
    dl_device = run_dl(settings['DL'], threads, stop_event, dl_callback)
    db_device = run_db(settings['DB'], threads, stop_event, db_callback)
    
    run_ds1(settings['DS1'], threads, stop_event, ds1_callback)
    run_dms(settings['DMS'], threads, stop_event, dms_callback)
    run_dus1(settings['DUS1'], threads, stop_event, dus1_callback)
    run_dpir1(settings['DPIR1'], threads, stop_event, dpir1_callback)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping PI1...')
        stop_event.set()
    finally:
        for t in threads:
            t.join()

        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("PI1 stopped.")

    # # OVAKOO za input_thread
    
    # in_thread = threading.Thread(target=input_thread, args=(dl_device, db_device, stop_event))
    # in_thread.daemon = True
    # in_thread.start()
    # threads.append(in_thread)

    # try:
    #     for t in threads: 
    #         t.join()
    # except KeyboardInterrupt:
    #     print('Stopping PI1...')
    #     stop_event.set()
    #     for t in threads: 
    #         t.join()
    #     mqtt_client.loop_stop()