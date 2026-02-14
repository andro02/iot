import time
import random

def run_dht_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    # pocetne vrednosti
    temperature = 25.0
    humidity = 60.0
    
    while not stop_event.is_set():
        temperature += random.uniform(-0.5, 0.5)
        humidity += random.uniform(-1, 1)
        
        # ogranicenja da ne ode u nerealne vrednosti
        if humidity < 0: humidity = 0
        if humidity > 100: humidity = 100
        
        # saljemo podatke nazad u main
        callback(humidity, temperature, publish_event, settings)
        
        time.sleep(delay)