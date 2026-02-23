import time
import random
import math

def run_dus1_simulator(delay, callback, stop_event):
    t = 0.0  # vreme za sinusoidu
    amplitude = 50   # maksimalna promena distance
    base_distance = 150  # srednja vrednost distance (cm)
    period = 20       # koliko iteracija traje jedan ciklus sinusoide
    
    while not stop_event.is_set():
        distance = base_distance + amplitude * math.sin(2 * math.pi * t / period)
        distance += random.uniform(-2, 2)
        distance = max(0, min(300, distance))

        callback(round(distance/3, 2))

        t += 1
        time.sleep(delay)