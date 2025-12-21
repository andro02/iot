try:
    import RPi.GPIO as GPIO
except:
    pass
import time

class DMS(object):
    def __init__(self, settings, callback):
        self.rows = [settings['R1'], settings['R2'], settings['R3'], settings['R4']]
        self.cols = [settings['C1'], settings['C2'], settings['C3'], settings['C4']]
        self.callback = callback
        
        for row in self.rows:
            GPIO.setup(row, GPIO.OUT)
        for col in self.cols:
            GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def read_key(self):
        chars = [
            ["1", "2", "3", "A"],
            ["4", "5", "6", "B"],
            ["7", "8", "9", "C"],
            ["*", "0", "#", "D"]
        ]
        for i, row in enumerate(self.rows):
            GPIO.output(row, GPIO.HIGH)
            for j, col in enumerate(self.cols):
                if GPIO.input(col) == 1:
                    GPIO.output(row, GPIO.LOW)
                    return chars[i][j]
            GPIO.output(row, GPIO.LOW)
        return None

def run_dms_loop(dms, stop_event):
    while not stop_event.is_set():
        key = dms.read_key()
        if key:
            dms.callback(key)
            time.sleep(0.3) # kratak sleep za debounce
        if stop_event.is_set():
            break
        time.sleep(0.1) 