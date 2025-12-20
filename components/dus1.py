import threading
import time
from simulators.dus1 import run_dus1_simulator

def dus1_callback(distance):
    t = time.localtime()
    print(f"[{time.strftime('%H:%M:%S', t)}] DUS1: Distance = {distance} cm")

def run_dus1(settings, threads, stop_event):
    if settings['simulated']:
        print("Starting DUS1 simulator.")
        t = threading.Thread(target=run_dus1_simulator, args=(3, dus1_callback, stop_event, settings['scan_delay']))
        t.start()
        threads.append(t)
    else:
        from sensors.dus1 import run_dus1_loop, DUS1
        print("Starting DUS1 loop.")
        dus1 = DUS1(settings['pin_trig'], settings['pin_echo'], settings['scan_delay'], dus1_callback)
        t = threading.Thread(target=run_dus1_loop, args=(dus1, stop_event))
        t.start()
        threads.append(t)