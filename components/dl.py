import threading
import time
from simulators.dl import run_dl_simulator

def run_dl(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DL simulation (Press 'L' to toggle)")
        dl_thread = threading.Thread(target=run_dl_simulator, args=(callback, stop_event))
        dl_thread.start()
        threads.append(dl_thread)
    else:
        from actuators.dl import run_dl_loop, DL
        print("Starting DL Real Loop (Press 'L' to toggle)")
        
        # Ovde prosledjujemo callback klasi/funkciji za pravi hardver
        door_light = DL(settings['pin'], callback)
        
        dl_thread = threading.Thread(target=run_dl_loop, args=(door_light, stop_event))
        dl_thread.start()
        threads.append(dl_thread)