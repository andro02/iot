import time

# Samo drzimo proces zivim jer je aktuator
def run_brgb_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    while not stop_event.is_set():
        time.sleep(1)