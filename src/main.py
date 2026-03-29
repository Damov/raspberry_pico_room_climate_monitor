import machine
from machine import Pin
from utime import sleep, time, ticks_ms, ticks_diff
import gc

from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_manager import ScreenManager
from screen_writer import ScreenWriter
from logger import Logger

from drivers.SCD41_driver import SCD41
from drivers.BME280_driver import BME280

from fonts import OpenSansBold_28, OpenSansBold_20

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
#-- Variables required to control the device with buttons -------------
    SCR_LAYOUT_NUMBER     = 0 #....................................... Screen layout number (0, 1, 2, ...) to control which screen layout is currently displayed
    SCR_MAX_LAYOUT_NUMBER = 4 #....................................... Maximum screen layout number (assuming we have 5 layouts: 0, 1, 2, 3, 4)
    SCR_FULL_REFRESH      = False #................................... Flag to indicate if a full screen refresh is requested by button press

#-- Define K1, K2, K3, K4 pins for future use -------------------------
    btn_K1 = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP) #... Define K1 pin as input with pull-up resistor on GP21
    btn_K2 = machine.Pin(20, machine.Pin.IN, machine.Pin.PULL_UP) #... Define K2 pin as input with pull-up resistor on GP20
    btn_K3 = machine.Pin(19, machine.Pin.IN, machine.Pin.PULL_UP) #... Define K3 pin as input with pull-up resistor on GP19
    btn_K4 = machine.Pin(18, machine.Pin.IN, machine.Pin.PULL_UP) #... Define K4 pin as input with pull-up resistor on GP18

#-- Set time refresh intervals to current time ------------------------
    last_full = ticks_ms()
    last_fast = ticks_ms()
    last_partial = ticks_ms()
    first_refresh = True

#-- Initialize the short-term Logger ----------------------------------
    MAX_BIN_HISTORY = 0.25 * 3600 #............... Keep 15 minutes of history in seconds
    BIN_TIMESPAN    = 0.5 * 60 #.................. Bin width of 30 seconds for output in seconds

    logger_pressure_shortterm = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 15 minutes of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 seconds for output
        )

    logger_temperature_shortterm = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 15 minutes of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 seconds for output
        )

    logger_humidity_shortterm = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 15 minutes of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 seconds for output
        )

    logger_co2_shortterm = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 15 minutes of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 seconds for output
        )

#-- Initialize the 24h-term Logger ----------------------------------
    MAX_BIN_HISTORY = 24 * 3600 #................. Keep 24 hours of history in seconds
    BIN_TIMESPAN    = 30 * 60 #................... Bin width of 30 minutes for output in seconds

    logger_pressure_24h = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 24 hours of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 minutes for output
        )

    logger_temperature_24h = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 24 hours of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 minutes for output
        )

    logger_humidity_24h = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 24 hours of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 minutes for output
        )

    logger_co2_24h = Logger(
            max_bin_history = MAX_BIN_HISTORY, #.. Keep 24 hours of history
            bin_timespan = BIN_TIMESPAN #......... Bin width of 30 minutes for output
        )

#-- Initialize the screen ---------------------------------------------
    epd = EPD_2in7_V2()

#-- Create a ScreenWriter instance ------------------------------------
    screen_writer = ScreenWriter(
            screen_driver = epd,
            font = OpenSansBold_28,
            verbose = True
        )
    
#-- Refresh screen --------------------------------------------------------
    screen_writer.show() #......................... First full refresh

#-- Show splash screen ------------------------------------------------
    fname = "img/splash_screen.bin"
    img_width  = 264
    img_height = 176

    screen_writer.add_image(
        fname,
        img_width,
        img_height,
        x=0,
        y=0,
        do_gc = True,
        show_after = False
    ) #............................. Add splash screen image to the screen

    screen_writer.change_font(OpenSansBold_20)
    screen_writer.add_text(
            "Loading...",
            85,
            155,
            invert=False
        ) #......................... Add "Loading..." text to the screen
    screen_writer.change_font(OpenSansBold_28)
    screen_writer.show() #.......... Show the splash screen with the loading message

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
            i2c_bus_id=1,
            scl_pin=3,
            sda_pin=2,
            address=0x62,
            freq=100000
        ) #............................................. Initialize SCD41 sensor
    
    while True:
    #-- Garbage collection to free up memory ------------------------------
        gc.collect() #..................................................... Run garbage collection to free up memory before the next loop iteration

    #-- Get data frm sensors ----------------------------------------------
        print_mem("before loop step")

        """
        CO2, temp, hum = sensor_scd41.read_measurement()
        _, pressure, _ = sensor_bme280.read_compensated()
        """

        CO2, _, _ = sensor_scd41.read_measurement()
        temp, pressure, hum = sensor_bme280.read_compensated()

        print_mem("after sensors")

    #-- Add new samples to the loggers ------------------------------------
        now_timestamp = ticks_ms() #............................. Current time in ms

        logger_pressure_shortterm.add(now_timestamp, pressure) #. Add new pressure sample to the short-term logger
        logger_temperature_shortterm.add(now_timestamp, temp) #.. Add new temperature sample to the short-term logger
        logger_humidity_shortterm.add(now_timestamp, hum) #...... Add new humidity sample to the short-term logger
        logger_co2_shortterm.add(now_timestamp, CO2) #........... Add new CO2 sample to the short-term logger

        logger_pressure_24h.add(now_timestamp, pressure) #....... Add new pressure sample to the short-term logger
        logger_temperature_24h.add(now_timestamp, temp) #........ Add new temperature sample to the 24h logger
        logger_humidity_24h.add(now_timestamp, hum) #............ Add new humidity sample to the 24h logger
        logger_co2_24h.add(now_timestamp, CO2) #................. Add new CO2 sample to the 24h logger

        print_mem("after logger")

    #-- Draw the first screen layout with the example data ----------------
        gc.collect() #..................................................... Run garbage collection to free up memory before the next loop iteration
        try:
            print(f"Drawing screen layout {SCR_LAYOUT_NUMBER} ...")
            if SCR_LAYOUT_NUMBER == 0:
                screen_manager.screen1(
                            temp,
                            hum,
                            pressure,
                            CO2,
                            logger_temperature_shortterm,
                            logger_humidity_shortterm,
                            logger_co2_shortterm
                    ) #.............................................. Draw the first screen layout with the latest sensor readings and loggers for short-term history
            elif SCR_LAYOUT_NUMBER == 1:
                screen_manager.screen2_24h_temperature_history(
                                temp,
                                logger_temperature_24h
                            )
            elif SCR_LAYOUT_NUMBER == 2:
                screen_manager.screen3_24h_humidity_history(
                                    hum,
                                    logger_humidity_24h
                            )
            elif SCR_LAYOUT_NUMBER == 3:
                screen_manager.screen4_24h_co2_history(
                                    CO2,
                                    logger_co2_24h
                            )
            elif SCR_LAYOUT_NUMBER == 4:
                screen_manager.screen5_24h_pressure_history(
                                    pressure,
                                    logger_pressure_24h
                            )
            else:
                raise ValueError(f"Invalid screen mode: {screen_mode}") #........ Raise an error if the screen mode is invalid (not 0 or 1)
        except MemoryError as e:
            print(f"MemoryError: {e}")

    #-- Update screen -----------------------------------------------------
        if first_refresh or SCR_FULL_REFRESH:
            screen_writer.show() #......................... First full refresh
            first_refresh = False
            SCR_FULL_REFRESH = False
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

    #-- Wait before the next update and check buttons ---------------------
        WAIT_INTERVAL_MS = 30 * 1000 #.......................... Wait 30 seconds before the next loop iteration
        start_wait       = ticks_ms() #......................... Current time in ms

        while ticks_diff(ticks_ms(), start_wait) < WAIT_INTERVAL_MS:
            DELAY_DEBOUNCE_MS = 0.20 #......................... Debounce delay to avoid multiple triggers from a single button press

            if btn_K1.value() == 0: #.......................... Check if K1 button is pressed (active low)
                print(
                    "K1 button press detected during wait, "
                    "refreshing screen immediately..."
                )
                SCR_FULL_REFRESH = True #...................... Flag to indicate if a full screen refresh is requested by button press
                sleep(DELAY_DEBOUNCE_MS) #..................... Sleep for a short time to debounce the button press and avoid multiple triggers
                break #........................................ Exit the waiting loop to update the screen immediately
            
            elif btn_K2.value() == 0: #........................ Check if K2 button is pressed (active low)
                print(
                    "K2 button press detected during wait, "
                    "going to previous screen immediately..."
                )
                SCR_LAYOUT_NUMBER -= 1 #....................... Decrease screen layout number to go to the previous screen
                if SCR_LAYOUT_NUMBER < 0:
                    SCR_LAYOUT_NUMBER = SCR_MAX_LAYOUT_NUMBER # Ensure screen layout number does not go below 0
                SCR_FULL_REFRESH = True #...................... Flag to indicate if a full screen refresh is requested by button press
                sleep(DELAY_DEBOUNCE_MS) #..................... Sleep for a short time to debounce the button press and avoid multiple triggers
                break #........................................ Exit the waiting loop to update the screen immediately
            
            elif btn_K3.value() == 0: #........................ Check if K3 button is pressed (active low)
                print(
                    "K3 button press detected during wait, "
                    "going to next screen immediately..."
                )
                SCR_LAYOUT_NUMBER += 1 #....................... Increase screen layout number to go to the next screen
                if SCR_LAYOUT_NUMBER > SCR_MAX_LAYOUT_NUMBER:
                    SCR_LAYOUT_NUMBER = 0 #.................... Ensure screen layout number does not exceed maximum
                SCR_FULL_REFRESH = True #...................... Flag to indicate if a full screen refresh is requested by button press
                sleep(DELAY_DEBOUNCE_MS) #..................... Sleep for a short time to debounce the button press and avoid multiple triggers
                break #........................................ Exit the waiting loop to update the screen immediately
            
            elif btn_K4.value() == 0: #........................ Check if K4 button is pressed (active low)
                print(
                    "K4 button press detected during wait, "
                    "returning back to home screen..."
                )
                SCR_LAYOUT_NUMBER = 0 #........................ Set screen layout number to 0 (home screen)
                SCR_FULL_REFRESH = True #...................... Flag to indicate if a full screen refresh is requested by button press
                sleep(DELAY_DEBOUNCE_MS) #..................... Sleep for a short time to debounce the button press and avoid multiple triggers
                break #........................................ Exit the waiting loop to update the screen immediately

    #-- Print a separator for the next loop iteration ---------------------
        print("Updating screen with new sensor readings...")
        print("-" * 50)


if __name__ == "__main__":
#-- Define on-board LED pin -----------------------------------------------
    error_led = machine.Pin("LED", machine.Pin.OUT) #................. On‑board LED (Pico default)

#-- Start execution of the main function and handle exceptions ------------
    try:
        error_led.value(1) #.......................................... Turn on the error LED
        main() #...................................................... Start the main function
    except Exception as e:
    #-- Write Exception to file -------------------------------------------
        file_path = "exception.log"
        write_exception_to_file(e, file_path=file_path)

    #-- Blink the LED to indicate an error --------------------------------
        while True:
            dT_interval = 0.5 # seconds
            error_led.value(1)
            sleep(dT_interval)
            error_led.value(0)
            sleep(dT_interval)
