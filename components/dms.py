import threading
import time
from simulators.dms import run_dms_simulator

def run_dms(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DMS simulator.")
        dms_thread = threading.Thread(target=run_dms_simulator, args=(2, callback, stop_event))
        dms_thread.start()
        threads.append(dms_thread)
    else:
        from sensors.dms import run_dms_loop, DMS
        print("Starting DMS loop.")
        dms = DMS(settings, callback)
        dms_thread = threading.Thread(target=run_dms_loop, args=(dms, stop_event))
        dms_thread.start()
        threads.append(dms_thread)