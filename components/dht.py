import threading
import time
from simulators.dht import run_dht_simulator

def run_dht(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_dht_simulator, args=(2, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
    else:
        from sensors.dht import DHTSensor
        sensor = DHTSensor(settings)
        
        def loop():
            while not stop_event.is_set():
                # citamo podatke sa pravog senzora
                hum, temp = sensor.read_data()
                
                # ako citanje uspesno (nije None), saljemo callback
                if hum is not None and temp is not None:
                    callback(hum, temp, None, settings)
                
                time.sleep(2) # DHT11 je spor, treba mu bar 1-2 sekunde pauze

        t = threading.Thread(target=loop)
        t.start()
        threads.append(t)