import machine
from utime import sleep, time, ticks_ms, ticks_diff
import gc

from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_manager import ScreenManager
from screen_writer import ScreenWriter
from logger import Logger

from drivers.SCD41_driver import SCD41
from drivers.BME280_driver import BME280

from fonts import OpenSansBold_28

def print_mem(label=""):
    """
        Print the current memory usage (free and allocated) 
        with an optional label for context.

        This function is useful for debugging memory usage at
        different points in the code.
    """
    #import gc #........................................................ Import garbage collector module to check memory usage
    #gc.collect() #..................................................... Run garbage collection to free up memory before checking usage
    print(
        label,
        f"alloc: {gc.mem_alloc()}, "
        f"free: {gc.mem_free()} ({100*gc.mem_free()/(gc.mem_free() + gc.mem_alloc()):.2f}) %"
    ) #................................................................. Print the label along with free and allocated memory in bytes for debugging purposes


def write_exception_to_file(e, file_path="exception.log"):
    """
        Write the exception string to file while overwriting the
        previous content if it exists.
        
        
        Arguments:
        ----------
        e : Exception
            The exception object to be logged.
        file_path: str
            The path to the log file where the exception should be written.
            
        Returns:
        --------
            None

        Notes:
        ------
        - This function attempts to write the exception string to a specified log file.
        - If the file cannot be written (e.g., due to filesystem issues), it will print
          an error message to the console instead.
        - The function does not raise exceptions itself; it handles any exceptions that
          occur during the file writing process internally.
    """
    try:
        import sys
        with open(file_path, "w") as f:
            sys.print_exception(e, f) #.......... Write the full exception traceback to the file
            f.flush() #.......................... Ensure data is written to the file immediately
    except Exception as e:
        # If logging fails, at least try to print
        print("Could not write exception to file:", e)
    return

def main():
    """
        Main function to initialize sensors, logger, and screen,
        and to continuously read sensor data, log it, and update the screen.
    """
#-- Set time refresh intervals to current time ------------------------
    last_full = ticks_ms()
    last_fast = ticks_ms()
    last_partial = ticks_ms()
    first_refresh = True

#-- Initialize the Logger ---------------------------------------------
    logger_shortterm = Logger(
            timedelta_seconds = 0.25 * 3600, #... Keep 15 minutes of history
            dt_seconds = 0.5*60 #................ Bin width of 30 seconds for output
        )
    
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
    
#-- Referesh screen -------------------------------------------------------
    screen_writer.show() #......................... First full refresh
    screen_writer.show() #......................... First full refresh
    screen_writer.show() #......................... First full refresh
    screen_writer.show() #......................... First full refresh
    
    while True:
    #-- Garbage collection to free up memory ------------------------------
        gc.collect() #..................................................... Run garbage collection to free up memory before the next loop iteration

    #-- Get data frm sensors ----------------------------------------------
        print_mem("before loop step")

        CO2, temp, hum = sensor_scd41.read_measurement()
        _, pressure, _ = sensor_bme280.read_compensated()

        print_mem("after sensors")

    #-- Log the new sample ------------------------------------------------
        logger_shortterm.add_sample(
            pressure = pressure,
            temperature = temp,
            humidity = hum,
            co2 = CO2
        )

        print_mem("after logger")

    #-- Draw the first screen layout with the example data ----------------
        screen_manager.screen1(temp, hum, pressure, CO2, logger_shortterm)

    #-- Update screen -----------------------------------------------------
        if first_refresh:
            screen_writer.show() #......................... First full refresh
            first_refresh = False
        else:
            FULL_INTERVAL_MS    = 15 * 60 * 1000   # 15 min
            FAST_INTERVAL_MS    = 5  * 60 * 1000   # 5 min
            PARTIAL_INTERVAL_MS = 5  * 1000        # 5 s

            now = ticks_ms() #................ Current time in ms

            # 1) Every 5 s: partial refresh
            if ticks_diff(now, last_partial) >= PARTIAL_INTERVAL_MS:
                last_partial = now
                screen_writer.show_partial()

            # 2) Every 5 min: fast refresh
            if ticks_diff(now, last_fast) >= FAST_INTERVAL_MS:
                last_fast = now
                screen_writer.show_fast()

            # 3) Every 15 min: full refresh
            if ticks_diff(now, last_full) >= FULL_INTERVAL_MS:
                last_full = now
                screen_writer.show()

        print_mem("after screen")

    #-- Wait before the next update ---------------------------------------
        sleep(5)
        print("Updating screen with new sensor readings...")

        print("\n\n\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
    #-- Write Exception to file -------------------------------------------
        file_path = "exception.log"
        write_exception_to_file(e, file_path=file_path)

    #-- Blink the LED to indicate an error --------------------------------
        error_led = machine.Pin("LED", machine.Pin.OUT) #................. On‑board LED (Pico default)

        while True:
            dT_interval = 0.5 # seconds
            error_led.value(1)
            sleep(dT_interval)
            error_led.value(0)
            sleep(dT_interval)
