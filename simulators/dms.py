import time
import random

def run_dms_simulator(delay, callback, stop_event):
    keys = ["1", "2", "3", "A", "4", "5", "6", "B", "7", "8", "9", "C", "*", "0", "#", "D"]
    while not stop_event.is_set():
        if random.random() < 0.2:
            key = random.choice(keys)
            callback(key)
            time.sleep(1)
        time.sleep(delay)