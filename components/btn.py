import threading
import time
from simulators.ds1 import run_ds1_simulator

def run_btn(settings, threads, stop_event, callback):
    print(f"Starting {settings['name']}")
    if settings['simulated']:
        # koristimo simulator od DS1 jer je logika dugmeta ista
        t = threading.Thread(target=run_ds1_simulator, args=(2, callback, stop_event))
        t.start()
        threads.append(t)
    else:
        from sensors.ds1 import run_ds1_loop, DS1
        # i driver od DS1 jer je isto
        btn = DS1(settings['pin'], settings['pull'], settings['bouncetime'], callback)
        t = threading.Thread(target=run_ds1_loop, args=(btn, stop_event))
        t.start()
        threads.append(t)