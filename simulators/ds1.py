import time
import random

def run_ds1_simulator(delay, callback, stop_event):
    while not stop_event.is_set():
        if random.random() < 0.4:
            callback(1)
            time.sleep(2)
            callback(0)
        time.sleep(delay)