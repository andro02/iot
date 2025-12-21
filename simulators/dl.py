import time

class DL(object):
    def __init__(self, pin):
        self.pin = pin
        self.state = False
    
    def turn_on(self):
        if not self.state:
            self.state = True
            t = time.localtime()
            print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT ON")
        
    def turn_off(self):
        if self.state:
            self.state = False
            t = time.localtime()
            print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT OFF")