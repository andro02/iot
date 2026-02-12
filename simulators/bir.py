import time
import random

# Tasteri iz tvog ir_receiver.py, random "hvata" dugme daljinskog
ButtonsNames = ["LEFT", "RIGHT", "UP", "DOWN", "2", "3", "1", "OK", "4", "5", "6", "7", "8", "9", "*", "0", "#"]

def run_bir_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    while not stop_event.is_set():
        # Simuliramo pritisak dugmeta svakih par sekundi
        time.sleep(random.randint(3, 6))
        
        if stop_event.is_set(): break
        
        key = random.choice(ButtonsNames)
        print(f"[{settings['name']}] Detected IR: {key}")
        callback(key, publish_event, settings)