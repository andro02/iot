import threading
import time
from simulators.dpir1 import run_dpir1_simulator

def dpir1_callback():
    t = time.localtime()
    print(f"[{time.strftime('%H:%M:%S', t)}] DPIR1: Motion DETECTED")

def run_dpir1(settings, threads, stop_event):
    if settings['simulated']:
        t = threading.Thread(target=run_dpir1_simulator, args=(3, dpir1_callback, stop_event))
        t.start()
        threads.append(t)
    else:
        from sensors.dpir1 import run_dpir1_loop, DPIR1
        dpir1 = DPIR1(settings['pin'], dpir1_callback)
        t = threading.Thread(target=run_dpir1_loop, args=(dpir1, stop_event))
        t.start()
        threads.append(t)