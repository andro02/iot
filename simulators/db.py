import time

def run_db_simulator(callback, stop_event):
    
    while not stop_event.is_set():
        time.sleep(0.1)