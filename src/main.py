"""
=============================================================================
main.py

Main script for the Raspberry Pico Room Climate Monitor. It initializes sensors,
logger, and screen, and continuously reads sensor data, logs it, and updates
the screen.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

import machine
from utime import sleep, sleep_ms, ticks_ms, ticks_diff
import gc

from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_manager import ScreenManager
from screen_writer import ScreenWriter
from logger import Logger
from button_controller import ButtonController, apply_button

from drivers.SCD41_driver import SCD41
from drivers.BME280_driver import BME280

from fonts import OpenSansBold_28, OpenSansBold_20

from error_handling import show_exception_on_screen, write_exception_to_file

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


def main():
    """Initialize button sampling and always stop it when the application exits."""
#-- Define active-low K1, K2, K3, K4 inputs ----------------------------
    pins = tuple(
        machine.Pin(number, machine.Pin.IN, machine.Pin.PULL_UP)
        for number in (21, 20, 19, 18)
    ) #............................................................... GP21 Refresh, GP20 Next, GP19 Previous, GP18 Home
    buttons = ButtonController(pins)
    try:
        _run_monitor(buttons)
    finally:
        buttons.close() #............................................. Stop the timer on errors and KeyboardInterrupt


def _run_monitor(buttons):
    """
        Initialize sensors, logger, and screen, then process button events
        independently of the periodic sensor measurements.
    """
#-- Variables required to control the device with buttons -------------
    SCR_LAYOUT_NUMBER     = 0 #....................................... Current screen layout (0-4)
    SCR_MAX_LAYOUT_NUMBER = 4 #....................................... Five available screen layouts
    SCR_FULL_REFRESH      = False #................................... Full refresh requested by a button event
    WAIT_INTERVAL_MS      = 30 * 1000 #............................... Sensor sampling interval in milliseconds
    draw_failures         = 0 #....................................... Consecutive failures while drawing the selected page
    last_measurement      = None #................................... Read sensors before drawing the first page

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
    #-- Check if a new sensor measurement is due --------------------------
        now = ticks_ms()
        measurement_due = (
            last_measurement is None or
            ticks_diff(now, last_measurement) >= WAIT_INTERVAL_MS
        )
        if measurement_due:
        #-- Read and log the latest sensor measurements -----------------------
            gc.collect() #................................ Free memory before reading the sensors
            print_mem("before loop step")

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

            last_measurement = ticks_ms() #................ Start the next interval after reading and logging

    #-- Apply one bounded batch of presses captured during any work -------
        for _ in range(buttons.pending()):
            button = buttons.pop()
            SCR_LAYOUT_NUMBER = apply_button(
                SCR_LAYOUT_NUMBER, button, SCR_MAX_LAYOUT_NUMBER + 1
            )
            SCR_FULL_REFRESH = True #...................... K1 also refreshes when the layout stays the same
            print(f"K{button} button released: screen layout {SCR_LAYOUT_NUMBER}")

        if buttons.take_overflow():
            print("Button queue full: new presses were discarded.")

    #-- Wait briefly when neither measurements nor buttons need drawing ---
        if not measurement_due and not SCR_FULL_REFRESH:
            sleep_ms(10) #................................ Avoid busy polling while the timer samples inputs
            continue

    #-- Draw the selected layout with the latest sensor data --------------
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
                raise ValueError(f"Invalid screen mode: {SCR_LAYOUT_NUMBER}") #........ Reject an invalid screen layout
        except MemoryError as e:
            draw_failures += 1
            print(f"MemoryError drawing layout {SCR_LAYOUT_NUMBER}: {e}")
            if draw_failures >= 3:
                raise #................................... Report persistent failures through the existing error handler
            SCR_FULL_REFRESH = True #...................... Retry the selected page without another button press
            gc.collect()
            sleep_ms(50)
            continue #.................................... Never refresh an incomplete frame after drawing fails
        draw_failures = 0

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


if __name__ == "__main__":
#-- Define on-board LED pin -----------------------------------------------
    error_led = machine.Pin("LED", machine.Pin.OUT) #................. On‑board LED (Pico default)

#-- Start execution of the main function and handle exceptions ------------
    try:
        error_led.value(1) #.......................................... Turn on the error LED
        main() #...................................................... Start the main function
    except Exception as e:
    #-- Write Exception to file -------------------------------------------
        write_exception_to_file(e, file_path="exception.log") #....... Write the exception traceback to a log file for later analysis
        show_exception_on_screen(e, show_traceback=False) #........... Display the exception on the e‑paper screen

    #-- Blink the LED to indicate an error --------------------------------
        while True:
            dT_interval = 0.5 # seconds
            error_led.value(1)
            sleep(dT_interval)
            error_led.value(0)
            sleep(dT_interval)
