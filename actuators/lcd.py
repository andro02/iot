from actuators.PCF8574 import PCF8574_GPIO
from actuators.Adafruit_LCD1602 import Adafruit_CharLCD

class LCD:
    def __init__(self, settings):
        self.address = int(settings['address'], 16) # npr. 0x27 pretvara u broj
        try:
            # Inicijalizacija GPIO adaptera (PCF8574)
            self.mcp = PCF8574_GPIO(self.address)
        except:
            # Fallback na alternativnu adresu ako prva ne radi (cesto je 0x3F)
            try:
                self.mcp = PCF8574_GPIO(0x3F)
            except:
                print('I2C Address Error for LCD!')
                return
            
        # uklj pozadinsko osvetljenje (backlight)
        self.mcp.output(3, 1)

        # Inicijalizacija LCD-a koristeci adapter
        self.lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=self.mcp)
        self.lcd.begin(16, 2) # 16 karaktera, 2 reda
        self.clear()

    def clear(self):
        self.lcd.clear()

    def print_text(self, text):
        # LCD biblioteka ocekuje string. "\n" prebacuje u novi red.
        self.lcd.clear()
        self.lcd.setCursor(0, 0)
        self.lcd.message(text)