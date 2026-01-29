import threading
import time
from simulators.dpir1 import run_dpir1_simulator

def run_dpir1(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DPIR1 simulator")
        t = threading.Thread(target=run_dpir1_simulator, args=(3, callback, stop_event))
        t.start()
        threads.append(t)
    else:
        from sensors.dpir1 import run_dpir1_loop, DPIR1
        print("Starting DPIR1 loop")
        dpir1 = DPIR1(settings['pin'], callback)
        t = threading.Thread(target=run_dpir1_loop, args=(dpir1, stop_event))
        t.start()
        threads.append(t)