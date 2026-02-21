import machine
from utime import sleep
from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_manager import ScreenManager
from screen_writer import ScreenWriter

from drivers.SCD41_driver import SCD41
from drivers.BME280_driver import BME280

from fonts import OpenSansBold_28

def main():
#-- Initialize the screen ---------------------------------------------
    epd = EPD_2in7_V2()

#-- Create a ScreenWriter instance ------------------------------------
    screen_writer = ScreenWriter(
            screen_driver = epd,
            font = OpenSansBold_28,
            verbose = True
        )

#-- Create a ScreenManager instance -----------------------------------
    screen_manager = ScreenManager(screen_writer)

#-- Init sensors ------------------------------------------------------
    sensor_bme280 = BME280(
            i2c_bus_id = 0,
            scl_pin = 1,
            sda_pin = 0,
            bme_addr = 0x77,
            freq=100000
        ) #............................................. Initialize BME280 sensor
    sensor_scd41 = SCD41(
            i2c_bus_id=0,
            scl_pin=1,
            sda_pin=0,
            address=0x62,
            freq=100000
        ) #............................................. Initialize SCD41 sensor
    
    while True:
    #-- Get data frm sensors ----------------------------------------------
        CO2, temp, hum = sensor_scd41.read_measurement()
        _, pressure, _ = sensor_bme280.read_compensated()

    #-- Draw the first screen layout with the example data ----------------
        screen_manager.screen1(temp, hum, pressure, CO2)

    #-- Update screen -----------------------------------------------------
        #screen_writer.show()
        #screen_writer.show_fast()
        screen_writer.show_partial()
    
    #-- Wait before the next update ---------------------------------------
        sleep(5)
        print("Updating screen with new sensor readings...")


if __name__ == "__main__":
    main()

