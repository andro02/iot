import threading
import time
from settings import load_settings
from components.ds1 import run_ds1
from components.dms import run_dms

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

if __name__ == "__main__":
    print('Starting app')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    try:
        run_ds1(settings['DS1'], threads, stop_event)
        run_dms(settings['DMS'], threads, stop_event)

        if settings['DL']['simulated']:
            from simulators.dl import DL
        else:
            from actuators.dl import DL
        
        door_light = DL(settings['DL']['pin'])

        print("Senzori (DS1 i DMS) rade u pozadini...")
        print("Glavna petlja testira DL (blinkanje)...\n")
        print("Pritisni CTRL+C za izlaz.\n")

        while True:
            door_light.turn_on()
            time.sleep(2)
            door_light.turn_off()
            time.sleep(2)

    except KeyboardInterrupt:
        print('Stopping app')
        stop_event.set()
        for t in threads:
            t.join()