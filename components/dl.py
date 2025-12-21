import threading
import time
from simulators.dl import run_dl_simulator

def dl_callback(state):
    status = "ON" if state else "OFF"
    t = time.localtime()
    print("-"*40)
    print(f"[{time.strftime('%H:%M:%S', t)}] Door Light: L pressed -> {status}")
    print("-"*40)

def run_dl(settings, threads, stop_event):
    if settings['simulated']:
        print("Starting DL simulation (Press 'L' to toggle)")
        dl_thread = threading.Thread(target=run_dl_simulator, args=(dl_callback, stop_event))
        dl_thread.start()
        threads.append(dl_thread)
    else:
        from actuators.dl import run_dl_loop, DL
        print("Starting DL loop")
        door_light = DL(settings['pin'], dl_callback)
        dl_thread = threading.Thread(target=run_dl_loop, args=(door_light, stop_event))
        dl_thread.start()
        threads.append(dl_thread)