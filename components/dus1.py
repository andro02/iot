import threading
import time
from simulators.dus1 import run_dus1_simulator

def run_dus1(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DUS1 simulator.")
        t = threading.Thread(target=run_dus1_simulator, args=(settings['scan_delay'], callback, stop_event))
        t.start()
        threads.append(t)
    else:
        from sensors.dus1 import run_dus1_loop, DUS1
        print("Starting DUS1 loop.")
        dus1 = DUS1(settings['pin_trig'], settings['pin_echo'], settings['scan_delay'], callback)
        t = threading.Thread(target=run_dus1_loop, args=(dus1, stop_event))
        t.start()
        threads.append(t)