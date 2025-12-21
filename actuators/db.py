import time
import keyboard
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

def run_db_loop(db, stop_event):

    def on_press(e):
        db.buzz_on()
        db.callback(True)

    def on_release(e):
        db.buzz_off()
        db.callback(False) 

    h1 = keyboard.on_press_key('b', on_press, suppress=True)
    h2 = keyboard.on_release_key('b', on_release, suppress=True)

    while not stop_event.is_set():
        time.sleep(0.1)

    keyboard.unhook(h1)
    keyboard.unhook(h2)
    db.buzz_off()