try:
    import RPi.GPIO as GPIO
except: 
    pass
import time

class DUS1(object):
    def init(self, trig_pin, echo_pin, scan_delay, callback):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.scan_delay = scan_delay
        self.callback = callback
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)

    def measure(self):
        GPIO.output(self.trig_pin, False)
        time.sleep(0.2)
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, False)

        pulse_start = time.time()
        pulse_end = time.time()
        timeout = time.time() + 0.1

        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
            if time.time() > timeout: return None

        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
            if time.time() > timeout: return None

        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2

        if distance > 0:
            self.callback(round(distance, 2))

def run_dus1_loop(dus1 : DUS1, stop_event):
    while True:
        dus1.measure()
        if stop_event.is_set():
            break

        time.sleep(dus1.scan_delay)