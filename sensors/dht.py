from sensors.LA_DHT import DHT
import RPi.GPIO as GPIO

class DHTSensor(object):
    def init(self, settings):
        self.pin = settings['pin']
        self.dht = DHT(self.pin)
        self.dht_lib = DHT  # Referenca na klasu zbog konstanti (DHTLIB_OK itd.)

    def read_data(self):
        # readDHT11 vraca status kod (0 je OK)
        check = self.dht.readDHT11()

        if check == self.dht_lib.DHTLIB_OK:
            # Ako je citanje uspesno, vrati tuple (vlaznost, temperatura)
            return self.dht.humidity, self.dht.temperature
        else:
            # U slucaju greske (checksum, timeout), vracamo None
            return None, None