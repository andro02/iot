import time

def run_lcd_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    # LCD obicno ceka poruke preko MQTT-a ili prikazuje senzore
    # Samo drzimo petlju
    while not stop_event.is_set():
        time.sleep(1)