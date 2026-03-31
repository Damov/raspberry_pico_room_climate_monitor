"""
=============================================================================
SCD41_driver.py

SCD41 sensor driver for MicroPython on Raspberry Pi Pico. It provides methods
to read CO2 concentration, temperature, and humidity from the SCD41 sensor.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

from machine import Pin, I2C
import time

class SCD41:
    """
        SCD41 sensor driver for MicroPython on Raspberry Pi Pico.

        This class provides methods to read CO2 concentration, temperature
        and humidity from the SCD41 sensor.

        Usage:
        ------
            scd41 = SCD41(i2c_bus_id=0, scl_pin=1, sda_pin=0, address=0x62)
            co2, temp, rh = scd41.read_measurement()
    """
    def __init__(
            self,
            i2c_bus_id=0,
            scl_pin=1,
            sda_pin=0,
            address=0x62,
            freq=100000
        ):
        """
            Initialize the SCD41 driver to read CO2 concentration, temperature and
            humidity.

            Arguments:
            ----------
                i2c_bus_id: I2C bus ID (default: 0)
                scl_pin: GPIO pin for SCL (default: 1)
                sda_pin: GPIO pin for SDA (default: 0)
                address: I2C address of SCD41 (default: 0x62)
                freq: I2C bus frequency (default: 100000)
            
            Returns:
            --------
                None
                    Constructor does not return any value
        """
    #-- I2C bus initialisation -----------------------------------------------
        self.i2c = I2C(
                    i2c_bus_id,
                    scl  = Pin(scl_pin),
                    sda  = Pin(sda_pin),
                    freq = freq
                ) #................................... I2C bus initialization with specified parameters
        self.address = address #...................... I2C address of the SCD4x chips

    #-- Last data from the sensor --------------------------------------------
        self.co2 = None #............................. Last read CO2 concentration in ppm
        self.temperature = None #..................... Last read temperature in °C
        self.humidity = None #........................ Last read relative humidity in %
    
    #-- Sensor initialisation ------------------------------------------------
        self._write_cmd(0x3F86) #..................... Stop periodic measurement
        time.sleep_ms(500)
        self._write_cmd(0x21B1) #..................... Start periodic measurement
        time.sleep(5) #............................... First measurement takes a few seconds
    
    #-- Return ---------------------------------------------------------------
        return

    def _write_cmd(self, cmd):
        """
            Write a 16-bit command to the SCD41 sensor.
            
            Arguments:
            ----------
                cmd: 16-bit command to send to the sensor
            
            Returns:
            --------
                None
                    This method does not return any value
        """
        buf = bytearray(2) #.............................. Create a 2-byte buffer to hold the command
        buf[0] = (cmd >> 8) & 0xFF #...................... Split the 16-bit command into two bytes
        buf[1] = cmd & 0xFF
        self.i2c.writeto(self.address, buf) #............. Write the command to the sensor over I2C

    #-- Return ---------------------------------------------------------------
        return

    def _crc8(self, msb, lsb):
        """
            Calculate SCD4x CRC-8 for one 16-bit data word.

            Arguments:
            ----------
                msb: Most significant byte of the word
                lsb: Least significant byte of the word

            Returns:
            --------
                crc: Calculated CRC-8 value
        """
        crc = 0xFF
        for byte in (msb, lsb):
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
    #-- Returns ---------------------------------------------------------------
        return crc

    def read_measurement(self):
        """
            Read CO2 concentration, temperature and humidity from the SCD41 sensor.

            Returns:
            --------
                co2: CO2 concentration in ppm
                temp: Temperature in °C
                rh: Relative humidity in %

            Raises:
            -------
                ValueError:
                    If CRC validation fails for any measurement word
        """
    #-- Read measurement data ------------------------------------------------------
        try:

            self._write_cmd(0xEC05) #..................... Read measurement command
            time.sleep_ms(5) #............................ Wait for the sensor to prepare the data

            data = self.i2c.readfrom(self.address, 9) #... Read 9 bytes of data (CO2, temperature, humidity + CRC)

            if self._crc8(data[0], data[1]) != data[2]:
                raise ValueError("SCD41 CRC check failed for CO2 word")
            if self._crc8(data[3], data[4]) != data[5]:
                raise ValueError("SCD41 CRC check failed for temperature word")
            if self._crc8(data[6], data[7]) != data[8]:
                raise ValueError("SCD41 CRC check failed for humidity word")

            co2_raw = (data[0] << 8) | data[1] #.......... Combine the first two bytes to get the raw CO2 value (16-bit)
            t_raw   = (data[3] << 8) | data[4] #.......... Combine the next two bytes to get the raw temperature value (16-bit)
            rh_raw  = (data[6] << 8) | data[7] #.......... Combine the next two bytes to get the raw humidity value (16-bit)
    
        #-- Convert raw values to physical units using data from the SCD41 datasheet ---
            co2 = co2_raw #................................ Convert to ppm
            temp = -45 + 175 * (t_raw / 65535.0) #......... Convert to °C
            rh = 100 * (rh_raw / 65535.0) #................ Convert to %

        #-- Store the last read values in the instance variables -------------------------
            self.co2 = co2
            self.temperature = temp
            self.humidity = rh

        except OSError as e:
        #-- Return last data for temp, co2 and rh if sensor is not responding ------------
            co2  = self.co2         if self.co2 is not None         else 0
            temp = self.temperature if self.temperature is not None else 0.0
            rh   = self.humidity    if self.humidity is not None    else 0.0

    #-- Return the measurements ------------------------------------------------------
        return co2, temp, rh

    def temperature(self):
        """
            Read and return only the temperature value in °C.

            Returns:
            --------
                temp: Temperature in °C
        """
        co2, temp, rh = self.read_measurement()
        return temp
    
    def humidity(self):
        """
            Read and return only the humidity value in %.

            Returns:
            --------
                rh: Relative humidity in %
        """
        co2, temp, rh = self.read_measurement()
        return rh
    
    def co2_concentration(self):
        """
            Read and return only the CO2 concentration in ppm.

            Returns:
            --------
                co2: CO2 concentration in ppm
        """
        co2, temp, rh = self.read_measurement()
        return co2


# + ==================================================================== +
# |                   TESTING AND EXAMPLE USAGE BELOW                    |
# + ==================================================================== +

if __name__ == "__main__":
#-- Configuration ------------------------------------------------------
    I2C_BUS_ID = 0
    SCL_PIN    = 1
    SDA_PIN    = 0
    SCD41_ADDR = 0x62
    FREQ       = 100_000

#-- Initialize SCD41 --------------------------------------------------
    scd41 = SCD41(
                i2c_bus_id = I2C_BUS_ID,
                scl_pin    = SCL_PIN,
                sda_pin    = SDA_PIN,
                address    = SCD41_ADDR,
                freq       = FREQ
            )
    
#-- Read measurements in a loop ---------------------------------------
    while True:
        try:
            co2, t, rh = scd41.read_measurement()
            print("SCD41 -> CO2: {} ppm, T: {:.2f} °C, RH: {:.1f} %".format(co2, t, rh))
        except OSError as e:
            print("I2C Fehler SCD41:", e)
        finally:
            time.sleep(1.0)
