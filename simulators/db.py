import time

def run_db_simulator(callback, stop_event):
    # Simulator ne čita tastaturu
    while not stop_event.is_set():
        time.sleep(0.1)