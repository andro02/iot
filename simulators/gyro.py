import time
import random

def run_gyro_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    while not stop_event.is_set():
        # Simuliramo vrednosti akcelerometra i ziroskopa
        accel = [random.uniform(-1, 1) for _ in range(3)]
        gyro = [random.uniform(-10, 10) for _ in range(3)]
        
        callback(accel, gyro, publish_event, settings)
        time.sleep(delay)