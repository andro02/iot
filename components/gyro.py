import threading
import time
from simulators.gyro import run_gyro_simulator

def run_gyro(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_gyro_simulator, args=(2, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
    else:
        from sensors.gyro import Gyro
        gyro = Gyro(settings)
        # Ovde bi isla petlja za citanje pravog ziroskopa
        def loop():
            while not stop_event.is_set():
                accel, rot = gyro.get_data()
                callback(accel, rot, None, settings)
                time.sleep(1)
        
        t = threading.Thread(target=loop)
        t.start()
        threads.append(t)