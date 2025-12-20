import time
try:
    import RPi.GPIO as GPIO
except:
    pass

class DS1(object):
    def __init__(self, pin, mode, bouncetime, callback):
        self.pin = pin
        self.mode = {"up": GPIO.PUD_UP, "down": GPIO.PUD_DOWN}[mode]
        self.bouncetime = bouncetime
        self.callback = callback
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.mode)

    def button_pressed(self):
        self.callback(1) 

    def button_released(self):
        self.callback(0)

    def start_detecting(self):
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.detect_change, bouncetime=self.bouncetime)

    def detect_change(self, channel):
        if GPIO.input(self.pin) == GPIO.LOW:
            self.button_pressed()
        else:
            self.button_released()

def run_ds1_loop(ds1, stop_event):
    ds1.start_detecting()
    while True:
        if stop_event.is_set():
            GPIO.remove_event_detect(ds1.pin)
            break
        time.sleep(0.1)