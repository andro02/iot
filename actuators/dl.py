try:
    import RPi.GPIO as GPIO
except:
    pass
import keyboard
import time

class DL(object):
    def __init__(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setup(self.pin, GPIO.OUT)

    def turn_on(self):
        GPIO.output(self.pin, GPIO.HIGH)

    def turn_off(self):
        GPIO.output(self.pin, GPIO.LOW)

def run_dl_loop(dl, stop_event):
    is_on = False
    
    def on_press(e):
        nonlocal is_on
        if e.event_type == keyboard.KEY_DOWN:
            is_on = not is_on
            if is_on:
                dl.turn_on()
            else:
                dl.turn_off()
            dl.callback(is_on)
    hook = keyboard.hook_key('l', on_press, suppress=True)
    
    while not stop_event.is_set():
        time.sleep(0.1)

    keyboard.unhook(hook)
    dl.turn_off()