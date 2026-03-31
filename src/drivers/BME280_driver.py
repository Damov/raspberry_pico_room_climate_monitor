"""
=============================================================================
BME280_driver.py

BME280 sensor driver for MicroPython on Raspberry Pi Pico. It provides methods
to read temperature, pressure, and humidity from the BME280 sensor.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

from machine import Pin, I2C
import time

class BME280:
    """
    BME280 sensor driver for MicroPython on Raspberry Pi Pico.
    This class provides methods to read temperature, pressure and humidity from the BME280 sensor.

    Usage:
    ------
        bme = BME280(i2c_bus_id=0, scl_pin=1, sda_pin=0, bme_addr=0x77)
        temp, pressure, humidity = bme.read_compensated()
    """
    def __init__(
            self,
            i2c_bus_id = 0,
            scl_pin = 1,
            sda_pin = 0,
            bme_addr = 0x77,
            freq=100000
        ):
        """
        BME280 driver to read temperature, pressure and humidity.
        
        Arguments:
        ----------
            i2c_bus_id: I2C bus ID (default: 0)
            scl_pin: GPIO pin for SCL (default: 1)
            sda_pin: GPIO pin for SDA (default: 0)
            bme_addr: I2C address of BME280 (default: 0x77)
            freq: I2C bus frequency (default: 100000)

        Returns:
        --------
            None
                Contructor does not return any value
        """

    #-- Initialise I2C bus -----------------------------------------------
        self.i2c = I2C(
                i2c_bus_id,
                scl = Pin(scl_pin),
                sda = Pin(sda_pin),
                freq = freq
            ) #................................... I2C bus initialization with specified parameters
        self.address = bme_addr #................. I2C address of BME280
    
    #-- Calibration data reading -----------------------------------------
        dig_T = self.i2c.readfrom_mem(self.address, 0x88, 6)
        dig_P = self.i2c.readfrom_mem(self.address, 0x8E, 18)
        dig_H1 = self.i2c.readfrom_mem(self.address, 0xA1, 1)
        dig_H2_H6 = self.i2c.readfrom_mem(self.address, 0xE1, 7)

        self.dig_T1 = dig_T[1] << 8 | dig_T[0]
        self.dig_T2 = self._to_signed(dig_T[3] << 8 | dig_T[2])
        self.dig_T3 = self._to_signed(dig_T[5] << 8 | dig_T[4])

        self.dig_P1 = dig_P[1] << 8 | dig_P[0]
        self.dig_P2 = self._to_signed(dig_P[3] << 8 | dig_P[2])
        self.dig_P3 = self._to_signed(dig_P[5] << 8 | dig_P[4])
        self.dig_P4 = self._to_signed(dig_P[7] << 8 | dig_P[6])
        self.dig_P5 = self._to_signed(dig_P[9] << 8 | dig_P[8])
        self.dig_P6 = self._to_signed(dig_P[11] << 8 | dig_P[10])
        self.dig_P7 = self._to_signed(dig_P[13] << 8 | dig_P[12])
        self.dig_P8 = self._to_signed(dig_P[15] << 8 | dig_P[14])
        self.dig_P9 = self._to_signed(dig_P[17] << 8 | dig_P[16])

        self.dig_H1 = dig_H1[0]
        self.dig_H2 = self._to_signed(dig_H2_H6[1] << 8 | dig_H2_H6[0])
        self.dig_H3 = dig_H2_H6[2]
        e4 = dig_H2_H6[3]
        e5 = dig_H2_H6[4]
        e6 = dig_H2_H6[5]
        self.dig_H4 = self._to_signed((e4 << 4) | (e5 & 0x0F))
        self.dig_H5 = self._to_signed((e6 << 4) | (e5 >> 4))
        self.dig_H6 = self._to_signed(dig_H2_H6[6])
    
    #-- Humidity oversampling x1 -----------------------------------------
        self.i2c.writeto_mem(self.address, 0xF2, b'\x01')
    #-- Temp & Pressure oversampling x1, Normal mode ---------------------
        self.i2c.writeto_mem(self.address, 0xF4, b'\x27')
    #-- Standby 0.5ms, Filter off ----------------------------------------
        self.i2c.writeto_mem(self.address, 0xF5, b'\xA0')

        self.t_fine = 0
    
    #-- Return -----------------------------------------------------------
        return

    def _to_signed(self, n):
        """
            Convert unsigned integer to signed integer (16-bit).
        """
        return n - 65536 if n > 32767 else n

    def _read_raw_data(self):
        """
            Read raw temperature, pressure and humidity data from BME280.
            
            Returns:
            --------
                adc_t: Raw temperature data (20-bit)
                adc_p: Raw pressure data (20-bit)
                adc_h: Raw humidity data (16-bit)
        """
        # 8 Bytes: pressure[3], temp[3], humidity[2][web:71]
        data = self.i2c.readfrom_mem(self.address, 0xF7, 8)
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        adc_h = (data[6] << 8) | data[7]
        return adc_t, adc_p, adc_h

    def read_compensated(self):
        """
            Read compensated temperature, pressure and humidity values. What is returned
            is the actual physical values after applying the compensation formulas using
            the calibration data.
            
            Returns:
            --------
                temp: Compensated temperature in °C
                pressure: Compensated pressure in hPa
                h: Compensated humidity in %
        """
        adc_t, adc_p, adc_h = self._read_raw_data()

    #-- Temperatur-Compensation --------------------------------------------------------
        var1 = ((adc_t / 16384.0) - (self.dig_T1 / 1024.0)) * self.dig_T2
        var2 = (((adc_t / 131072.0) - (self.dig_T1 / 8192.0)) ** 2) * self.dig_T3
        self.t_fine = int(var1 + var2)
        temp = (var1 + var2) / 5120.0

    #-- Pressure-Compensation ----------------------------------------------------------
        var1 = self.t_fine / 2.0 - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = var2 / 4.0 + self.dig_P4 * 65536.0
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1
        if var1 == 0:
            pressure = 0
        else:
            p = 1048576.0 - adc_p
            p = (p - var2 / 4096.0) * 6250.0 / var1
            var1 = self.dig_P9 * p * p / 2147483648.0
            var2 = p * self.dig_P8 / 32768.0
            p = p + (var1 + var2 + self.dig_P7) / 16.0
            pressure = p / 100.0  # hPa
    
    #-- Humidity-Compensation ----------------------------------------------------------
        h = self.t_fine - 76800.0
        h = (adc_h - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) * \
            (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h *
            (1.0 + self.dig_H3 / 67108864.0 * h)))
        h = h * (1.0 - self.dig_H1 * h / 524288.0)
        if h > 100.0:
            h = 100.0
        elif h < 0.0:
            h = 0.0
    
    #-- Return -------------------------------------------------------------------------
        return temp, pressure, h
    

    def temperature(self):
        """
            Read and return only the compensated temperature value in °C.

            Returns:
            --------
                temp: Compensated temperature in °C
        """
        temp, _, _ = self.read_compensated()
        return temp
    
    def pressure(self):
        """
            Read and return only the compensated pressure value in hPa.

            Returns:
            --------
                pressure: Compensated pressure in hPa
        """
        _, pressure, _ = self.read_compensated()
        return pressure
    
    def humidity(self):
        """
            Read and return only the compensated humidity value in %.
            
            Returns:
            --------
                humidity: Compensated humidity in %
        """
        _, _, h = self.read_compensated()
        return h


# + ==================================================================== +
# |                   TESTING AND EXAMPLE USAGE BELOW                    |
# + ==================================================================== +

if __name__ == "__main__":
#-- Configuration ------------------------------------------------------
    I2C_BUS_ID = 0
    SCL_PIN    = 1
    SDA_PIN    = 0
    BME_ADDR   = 0x77

#-- Initialize BME280 --------------------------------------------------
    bme = BME280(
            i2c_bus_id = I2C_BUS_ID,
            scl_pin = SCL_PIN,
            sda_pin = SDA_PIN,
            bme_addr = BME_ADDR,
            freq = 100_000
          )
#-- Plot readings ------------------------------------------------------
    while True:
        t, p, h = bme.read_compensated()
        print("BME280 -> T: {:.2f} °C, P: {:.1f} hPa, RH: {:.1f} %".format(t, p, h))
        time.sleep(2)
