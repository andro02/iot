try:
    import RPi.GPIO as GPIO
except:
    pass

class BRGB(object):
    def __init__(self, settings):
        self.RED_PIN = settings['pin_r']
        self.GREEN_PIN = settings['pin_g']
        self.BLUE_PIN = settings['pin_b']
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RED_PIN, GPIO.OUT)
        GPIO.setup(self.GREEN_PIN, GPIO.OUT)
        GPIO.setup(self.BLUE_PIN, GPIO.OUT)

    def turnOff(self):
        GPIO.output(self.RED_PIN, GPIO.LOW)
        GPIO.output(self.GREEN_PIN, GPIO.LOW)
        GPIO.output(self.BLUE_PIN, GPIO.LOW)

    def set_color(self, color):
        self.turnOff()
        if color == "red":
            GPIO.output(self.RED_PIN, GPIO.HIGH)
        elif color == "green":
            GPIO.output(self.GREEN_PIN, GPIO.HIGH)
        elif color == "blue":
            GPIO.output(self.BLUE_PIN, GPIO.HIGH)
        elif color == "white":
            GPIO.output(self.RED_PIN, GPIO.HIGH)
            GPIO.output(self.GREEN_PIN, GPIO.HIGH)
            GPIO.output(self.BLUE_PIN, GPIO.HIGH)