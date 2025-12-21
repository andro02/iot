import time
import random

def run_dpir1_simulator(delay, callback, stop_event):
    while True:
        motion = random.choice([True, False])
        if motion:
            callback()
        if stop_event.is_set():
            break
        time.sleep(delay)