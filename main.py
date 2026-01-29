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

        while(True):
            time.sleep(1)

    except KeyboardInterrupt:
        print('Stopping app')
        stop_event.set()
        for t in threads:
            t.join()