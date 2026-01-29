try:
    import RPi.GPIO as GPIO
except ImportError:
    pass

class DB(object):
    def init(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setup(self.pin, GPIO.OUT)

    def buzz_on(self):
        GPIO.output(self.pin, GPIO.HIGH)

    def buzz_off(self):
        GPIO.output(self.pin, GPIO.LOW)