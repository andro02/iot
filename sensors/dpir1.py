try:
    import RPi.GPIO as GPIO
except:
    pass

class DPIR1(object):
    def __init__(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setup(self.pin, GPIO.IN)

    def motion_detected(self, channel):
        state = GPIO.input(self.pin)
        if state == GPIO.HIGH:
            self.callback(True)   # ima pokreta
        else:
            self.callback(False)  # nema pokreta

    def start_detecting(self):
        GPIO.add_event_detect(
            self.pin,
            GPIO.BOTH,                
            callback=self.motion_detected,
            bouncetime=100
        )

def run_dpir1_loop(dpir1, stop_event):
    dpir1.start_detecting()
    while True:
        if stop_event.is_set():
            GPIO.remove_event_detect(dpir1.pin)
            break