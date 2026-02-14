try:
    import smbus
except:
    pass
import time

class LCD:
    def __init__(self, settings):
        self.bus = smbus.SMBus(settings['i2c_bus'])
        self.addr = int(settings['address'], 16)
        self.init_display()

    def write_word(self, data):
        temp = data
        if self.BL: temp |= 0x08 # ukljucuje se backlit
        else: temp &= 0xF7       # iskljucuje se backlit bit
        self.bus.write_byte(self.addr, temp)

    def send_command(self, comm):
        buf = comm & 0xF0       # za gornja 4 bita
        buf |= 0x04             # enable na high
        self.write_word(buf)
        time.sleep(0.002)
        buf &= 0xFB             # eneable na low
        self.write_word(buf)
        buf = (comm & 0x0F) << 4
        buf |= 0x04 
        self.write_word(buf)
        time.sleep(0.002)
        buf &= 0xFB 
        self.write_word(buf)

    def send_data(self, data):
        buf = data & 0xF0
        buf |= 0x05         # dodaje 1 za rec
        self.write_word(buf)
        time.sleep(0.002)
        buf &= 0xFB 
        self.write_word(buf)
        buf = (data & 0x0F) << 4
        buf |= 0x05 
        self.write_word(buf)
        time.sleep(0.002)
        buf &= 0xFB 
        self.write_word(buf)

    def init_display(self):
        self.BL = True
        try:
            self.send_command(0x33)
            time.sleep(0.005)
            self.send_command(0x32)
            time.sleep(0.005)
            self.send_command(0x28)
            time.sleep(0.005)
            self.send_command(0x0C)
            time.sleep(0.005)
            self.send_command(0x01)
            self.bus.write_byte(self.addr, 0x08)
        except:
            pass

    def clear(self):
        self.send_command(0x01)

    def write_text(self, text, line=1):
        if line == 1: self.send_command(0x80) # pocetak prvog reda
        if line == 2: self.send_command(0xC0) # pocetak drugog reda
        for char in text:
            self.send_data(ord(char))