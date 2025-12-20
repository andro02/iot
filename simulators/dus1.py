import time
import random

def run_dus1_simulator(delay, callback, stop_event):
    dist = 200
    while True:
        dist += random.choice([-5, -2, 0, 2, 5])
        if dist < 0: dist = 0
        if dist > 300: dist = 300

        callback(dist)
        if stop_event.is_set():
            break
        time.sleep(delay)