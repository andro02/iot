from sensors.MPU6050 import MPU6050

class Gyro(object):
    def __init__(self, settings):
        # MPU6050 biblioteka ocekuje bus i adresu
        self.mpu = MPU6050(settings['i2c_bus'], int(settings['address'], 16))
        self.mpu.dmp_initialize()

    def get_data(self):
        accel = self.mpu.get_acceleration()
        gyro = self.mpu.get_rotation()
        # Vracamo u formatu pogodnom za slanje
        return accel, gyro