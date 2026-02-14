try:
    import RPi.GPIO as GPIO
except:
    pass
from datetime import datetime
import time

class BIR(object):
    def __init__(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        # heksadecimalni kodovi tastera
        self.Buttons = [0x300ff22dd, 0x300ffc23d, 0x300ff629d, 0x300ffa857, 0x300ff9867, 0x300ffb04f, 0x300ff6897, 0x300ff02fd, 0x300ff30cf, 0x300ff18e7, 0x300ff7a85, 0x300ff10ef, 0x300ff38c7, 0x300ff5aa5, 0x300ff42bd, 0x300ff4ab5, 0x300ff52ad]
        self.ButtonsNames = ["LEFT", "RIGHT", "UP", "DOWN", "2", "3", "1", "OK", "4", "5", "6", "7", "8", "9", "*", "0", "#"]

    def getBinary(self):
        num1s = 0
        binary = 1
        command = []
        previousValue = 0
        value = GPIO.input(self.pin)
        
        while value:
            time.sleep(0.0001)
            value = GPIO.input(self.pin)
            
        startTime = datetime.now()
        
        while True:
            if previousValue != value:
                now = datetime.now()
                pulseTime = now - startTime
                startTime = now
                command.append((previousValue, pulseTime.microseconds))
                
            if value: num1s += 1
            else: num1s = 0
            
            if num1s > 10000: break
                
            previousValue = value
            value = GPIO.input(self.pin)
            
        for (typ, tme) in command:
            if typ == 1:
                if tme > 1000: binary = binary *10 +1 # duzina impulsa se pretvara u bitove
                else: binary *= 10
                
        if len(str(binary)) > 34:
            binary = int(str(binary)[:34])
            
        return binary

    def convertHex(self, binaryValue):
        tmpB2 = int(str(binaryValue),2)
        return hex(tmpB2)

    def loop(self):
        while True:
            inData = self.convertHex(self.getBinary()) #citaj signal
            for button in range(len(self.Buttons)): # prolazak kroz poznate dugmice
                if hex(self.Buttons[button]) == inData:
                    self.callback(self.ButtonsNames[button])