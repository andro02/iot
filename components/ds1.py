import threading
import time
from simulators.ds1 import run_ds1_simulator

def ds1_callback(pressed):
    t = time.localtime()
    if pressed:
        state = "PRESSED: Door unlocked!"  
    else:
        state = "RELEASED: Door locked!"
    print(f"[{time.strftime('%H:%M:%S', t)}] DS1: {state}")

def run_ds1(settings, threads, stop_event):
    if settings['simulated']:
        print("Starting DS1 simulator.")
        ds1_thread = threading.Thread(target=run_ds1_simulator, args=(5, ds1_callback, stop_event))
        ds1_thread.start()
        threads.append(ds1_thread)
    else:
        from sensors.ds1 import run_ds1_loop, DS1
        print("Starting DS1 loop.")
        ds1 = DS1(settings['pin'], settings['pull'], settings['bouncetime'], ds1_callback)
        ds1_thread = threading.Thread(target=run_ds1_loop, args=(ds1, stop_event))
        ds1_thread.start()
        threads.append(ds1_thread)