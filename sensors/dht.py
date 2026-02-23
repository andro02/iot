from sensors.LA_DHT import DHT
try:
    import RPi.GPIO as GPIO
except:
    pass

class DHTSensor(object):
    def __init__(self, settings):
        self.pin = settings['pin']
        self.dht = DHT(self.pin)
        self.dht_lib = DHT  # Referenca na klasu zbog konstanti (DHTLIB_OK itd.)

    def read_data(self):
        # readDHT11 vraca status kod (0 je OK)
        check = self.dht.readDHT11()

        if check == self.dht_lib.DHTLIB_OK:
            # Ako je citanje uspesno, vrati tuple (vlaznost, temperatura)
            return self.dht.humidity, self.dht.temperature
        elif(check is self.dht.DHTLIB_ERROR_CHECKSUM): #data check has errors
            print("DHTLIB_ERROR_CHECKSUM!!")
            return None, None
        elif(check is self.dht.DHTLIB_ERROR_TIMEOUT):  #reading DHT times out
            print("DHTLIB_ERROR_TIMEOUT!")
            return None, None
        else:
            # U slucaju greske (checksum, timeout), vracamo None
            return None, None