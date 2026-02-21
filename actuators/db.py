try:
    import RPi.GPIO as GPIO
except ImportError:
    pass
import time
import threading

class DB(object):
    def __init__(self, settings):
        self.pin = settings['pin']
        self.pitch = settings.get('pitch', 440) 
        self.is_buzzing = False
        self.running = True
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        # pozadinska nit koja ceka da is_buzzing postane True
        self.thread = threading.Thread(target=self._buzz_loop)
        self.thread.start()

    def _buzz_loop(self):
        period = 1.0 / self.pitch
        delay = period / 2
        
        while self.running:
            if self.is_buzzing:
                # Brzo paljenje i gasenje (PWM u softveru)
                GPIO.output(self.pin, True)
                time.sleep(delay)
                GPIO.output(self.pin, False)
                time.sleep(delay)
            else:
                # Ako ne zuji, spava malo duze
                time.sleep(0.05)

    def turn_on(self):
        """Metoda koju zovemo iz main.py / server.py da upalimo alarm"""
        self.is_buzzing = True

    def turn_off(self):
        """Metoda koju zovemo da ugasimo alarm"""
        self.is_buzzing = False
        GPIO.output(self.pin, False)

    def stop(self):
        """Gasi thread kada se zaustavi ceo program"""
        self.running = False
        self.is_buzzing = False
        self.thread.join()
        GPIO.output(self.pin, False)