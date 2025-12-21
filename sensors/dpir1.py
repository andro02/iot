try:
    import RPi.GPIO as GPIO
except:
    pass

class DPIR1(object):
    def init(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setup(self.pin, GPIO.IN)

    def motion_detected(self, channel):
        self.callback()

    def start_detecting(self):
        GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.motion_detected, bouncetime=100)

def run_dpir1_loop(dpir1, stop_event):
    dpir1.start_detecting()
    while True:
        if stop_event.is_set():
            GPIO.remove_event_detect(dpir1.pin)
            break