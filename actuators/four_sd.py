try:
    import RPi.GPIO as GPIO
except:
    pass
import time
import threading

class FourSD(object):
    def __init__(self, settings):
        self.segments = settings['segments']
        self.digits = settings['digits']
        
        GPIO.setmode(GPIO.BCM)
        for segment in self.segments:
            GPIO.setup(segment, GPIO.OUT)
            GPIO.output(segment, 0)
        for digit in self.digits:
            GPIO.setup(digit, GPIO.OUT)
            GPIO.output(digit, 1)
            
        self.num = {' ': (0,0,0,0,0,0,0),
                    '0': (1,1,1,1,1,1,0),
                    '1': (0,1,1,0,0,0,0),
                    '2': (1,1,0,1,1,0,1),
                    '3': (1,1,1,1,0,0,1),
                    '4': (0,1,1,0,0,1,1),
                    '5': (1,0,1,1,0,1,1),
                    '6': (1,0,1,1,1,1,1),
                    '7': (1,1,1,0,0,0,0),
                    '8': (1,1,1,1,1,1,1),
                    '9': (1,1,1,1,0,1,1)}
        
        self.current_time_str = "0000"
        self.running = True
        self.thread = threading.Thread(target=self._refresh_display)
        self.thread.start()

    def _refresh_display(self):
        while self.running:
            n = time.ctime()[11:13] + time.ctime()[14:16] # uzimmamo sate i minute za vreme
            s = str(n).rjust(4)
            for digit in range(4):
                for loop in range(0, 7):
                    GPIO.output(self.segments[loop], self.num[s[digit]][loop]) # pali/gasi 7 dioda tako da formiraju broj
                GPIO.output(self.digits[digit], 0) # spusta se napon, tj pali cifra
                time.sleep(0.001)
                GPIO.output(self.digits[digit], 1) # gasi cifru, prelazi na sledecu

    def stop(self):
        self.running = False
        self.thread.join()