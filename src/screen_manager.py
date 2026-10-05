"""
=============================================================================
screen_manager.py

Screen manager for the e-ink display. It defines the different screen layouts
and manages the drawing of data onto the display.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

import machine
import math
from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_writer import ScreenWriter

from fonts import OpenSansBold_12, OpenSansBold_20, OpenSansBold_28 #..... Load fonts

class ScreenManager:
    """
        Draws the screen with actual data onto the e-ink display. It
        manages the different screen layouts and their updates.
    """
    def __init__(self, screen_writer, altitude_m=0.0):
    #-- Save attributes -----------------------------------------------
        self.screen_writer = screen_writer
        self.altitude_m = altitude_m #........................ Height above sea level in metres
        self._pressure_factor = (1 - altitude_m / 44330.0) ** -5.255
    
    #-- Return --------------------------------------------------------
        return

    def screen1(
            self,
            temp,
            hum,
            pressure,
            CO2,
            logger_temperature_shortterm,
            logger_humidity_shortterm,
            logger_co2_shortterm
        ):
        """
            Draws the CO2 gauge and climate readings on the start screen.
            Short-term logger arguments are retained for caller compatibility.

            Arguments:
            ----------
                temp: float
                    Temperature in Celsius
                hum: float
                    Humidity in percentage
                pressure: float
                    Pressure in hPa
                CO2: float
                    CO2 concentration in ppm
                logger_temperature_shortterm: Logger
                    Logger instance to retrieve historical data 
                    for the temperature (unused on this layout)
                logger_humidity_shortterm: Logger
                    Logger instance to retrieve historical data 
                    for the humidity (unused on this layout)
                logger_co2_shortterm: Logger
                    Logger instance to retrieve historical data 
                    for the CO2 (unused on this layout)
            
            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
    #-- Draw the new start screen on a white background ----------------
        self.screen_writer.clear_fb(color=0xFF)
        fb = self.screen_writer.fb
        fb.vline(136, 8, 160, 0x00) #........................ Separate CO2 from the climate readings
        fb.line(136, 57, 263, 57, 0x00) #................... Separate temperature from humidity
        fb.line(136, 111, 263, 111, 0x00) #................. Separate humidity from pressure

    #-- Draw CO2 scale, assessment, and current value -------------------
        self._draw_co2_gauge(CO2)

    #-- Place larger climate symbols beside their values ---------------
        self.screen_writer.add_image("img/thermometer.bin", 16, 32, x=143, y=12,
                                     invert_colors=False, show_after=False)
        self._start_text(f"{temp:2.1f} °C", 168, 260, 14, center_y=28)
        self.screen_writer.add_image("img/water-drop.bin", 22, 32, x=140, y=66,
                                     invert_colors=False, show_after=False)
        self._start_text(f"{hum:2.1f} %", 168, 260, 68, center_y=82)
    #-- Show pressure and status without a heading or symbol ------------
        sea_pressure = self._sea_level_pressure(pressure)
        self._start_text(f"{sea_pressure:.1f} hPa", 145, 260, 122,
                         (OpenSansBold_20, OpenSansBold_12))
        self._start_text(self._pressure_status(sea_pressure), 145, 260, 148,
                         (OpenSansBold_20, OpenSansBold_12))
        self.screen_writer.change_font(OpenSansBold_28) #.... Restore the default font for other pages
        return

    def _start_text(self, text, x_start, x_end, y, fonts=None, center_y=None):
        """Center one line in its column, selecting a font that fits."""
        if fonts is None:
            fonts = (OpenSansBold_28, OpenSansBold_20, OpenSansBold_12)
        for font in fonts:
            self.screen_writer.change_font(font)
            if self.screen_writer.writer.stringlen(text) <= x_end - x_start:
                if center_y is not None:
                    y = center_y - font.height() // 2 #..... Keep smaller fallback fonts aligned with the icon
                self.screen_writer.add_text_horizontal_center(
                    text, y, x_start=x_start, x_end=x_end, invert=True)
                return
        raise ValueError("Start-screen text exceeds its column: " + text)

    def _sea_level_pressure(self, pressure):
        """Approximate sea-level pressure using the standard atmosphere."""
        return pressure * self._pressure_factor

    @staticmethod
    def _pressure_status(pressure):
        """Use broad display thresholds, rather than a weather forecast."""
        if pressure < 1000:
            return "Low"
        if pressure > 1020:
            return "High"
        return "Normal"

    @staticmethod
    def _co2_status(co2):
        """Preserve the existing CO2 assessment thresholds."""
        if co2 < 800:
            return "Good"
        if co2 < 1200:
            return "Medium"
        if co2 < 2000:
            return "Bad"
        return "Very Bad"

    @staticmethod
    def _co2_angle(co2):
        """Map 400..2500 ppm onto a 270-degree arc, clamping the fill level."""
        return (135 + 270 * (min(2500, max(400, co2)) - 400) / 2100) * math.pi / 180

    def _draw_co2_gauge(self, co2):
        """Draw an eight-pixel ring filled up to the current CO2 value."""
        fb = self.screen_writer.fb
        cx, cy = 67, 82
        self.screen_writer.change_font(OpenSansBold_20)
        heading_width = self.screen_writer.writer.stringlen("CO2")
        heading_x = (135 - heading_width - 5 - 18) // 2 #.... Center the CO2 heading and leaf as one group
        self.screen_writer.add_text("CO2", heading_x, 5, invert=True)
        self.screen_writer.add_image("img/leaf.bin", 18, 18,
                                     x=heading_x + heading_width + 5, y=6,
                                     invert_colors=False, show_after=False)

    #-- Fill four separated sectors without an extra image buffer ------
        boundaries = (400, 800, 1200, 2000, 2500)
        angles = tuple(self._co2_angle(value) for value in boundaries)
        fill_angle = self._co2_angle(co2)
        sectors = []
        for sector in range(4):
            start = angles[sector] + 0.105 #................ Inset cap centres to preserve the gaps
            end = angles[sector + 1] - 0.105
            filled_end = min(end, max(start, fill_angle))
            sectors.append((start, end, filled_end,
                            (50 * math.cos(start), 50 * math.sin(start)),
                            (50 * math.cos(end), 50 * math.sin(end)),
                            (50 * math.cos(filled_end), 50 * math.sin(filled_end)),
                            co2 > boundaries[sector]))
        for dy in range(-53, 54):
            for dx in range(-53, 54):
                distance = dx * dx + dy * dy
                if distance < 46 * 46 or distance >= 54 * 54:
                    continue
                angle = math.atan2(dy, dx)
                if angle < angles[0]:
                    angle += 2 * math.pi
                radial_distance = (math.sqrt(distance) - 50) ** 2
                for start, end, filled_end, first, last, filled_last, active in sectors:
                    if angle < start - 0.08 or angle > end + 0.08:
                        continue
                    track_distance = self._arc_distance_sq(
                        dx, dy, angle, start, end, first, last, radial_distance)
                    if track_distance >= 16:
                        continue
                    outline = track_distance >= 4 #........ Two-pixel contour around the rounded band
                    filled = active and self._arc_distance_sq(
                        dx, dy, angle, start, filled_end, first, filled_last,
                        radial_distance) < 16
                    fb.pixel(cx + dx, cy + dy, 0x00 if outline or filled else 0xFF)
                    break

    #-- Keep the assessment inside the arc and ppm beneath it -----------
        self._start_text(self._co2_status(co2), 22, 112, 71,
                         (OpenSansBold_20, OpenSansBold_12))
        self._start_text("400", 9, 41, 120, (OpenSansBold_12,))
        self._start_text("2500", 91, 130, 120, (OpenSansBold_12,))
        self._start_text(f"{co2:.0f}", 5, 130, 133)
        self._start_text("ppm", 5, 130, 163, (OpenSansBold_12,))
        return

    @staticmethod
    def _arc_distance_sq(dx, dy, angle, start, end, first, last, radial_distance):
        """Distance to an arc centreline, including circular end caps."""
        if angle < start:
            return (dx - first[0]) ** 2 + (dy - first[1]) ** 2
        if angle > end:
            return (dx - last[0]) ** 2 + (dy - last[1]) ** 2
        return radial_distance


    def screen2_24h_temperature_history(
            self,
            current_value,
            logger
        ):
        """
            Draws 24h temperature history as a barplot on the second
            screen layout.

            Arguments:
            ----------
                current_value: float
                    Current temperature in Celsius
                logger: Logger
                    Logger instance to retrieve historical data for the temperature

            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
        self._screen2_template(
                    current_value = current_value,
                    logger = logger,
                    unit = "°C",
                    title = "24h Temperature History"
                )
    #-- Return --------------------------------------------------------
        return

    def screen3_24h_humidity_history(
            self,
            current_value,
            logger
        ):
        """
            Draws 24h humidity history as a barplot on the third
            screen layout.

            Arguments:
            ----------
                current_value: float
                    Current humidity in percentage
                logger: Logger
                    Logger instance to retrieve historical data for the humidity

            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
        self._screen2_template(
                    current_value = current_value,
                    logger = logger,
                    unit = "%",
                    title = "24h Humidity History"
                )
    #-- Return --------------------------------------------------------
        return

    def screen4_24h_co2_history(
            self,
            current_value,
            logger
        ):
        """
            Draws 24h CO2 history as a barplot on the fourth
            screen layout.

            Arguments:
            ----------
                current_value: float
                    Current CO2 concentration in ppm
                logger: Logger
                    Logger instance to retrieve historical data for the CO2

            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
        self._screen2_template(
                    current_value = current_value,
                    logger = logger,
                    unit = "ppm",
                    title = "24h CO2 History"
                )
    #-- Return --------------------------------------------------------
        return

    def screen5_24h_pressure_history(
            self,
            current_value,
            logger
        ):
        """
            Draws 24h pressure history as a barplot on the fifth
            screen layout.

            Arguments:
            ----------
                current_value: float
                    Current pressure in hPa
                logger: Logger
                    Logger instance to retrieve historical data for the pressure

            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
        self._screen2_template(
                    current_value = current_value,
                    logger = logger,
                    unit = "hPa",
                    title = "24h Pressure History"
                )
    #-- Return --------------------------------------------------------
        return

    def _screen2_template(
            self,
            current_value,
            logger,
            unit = "",
            title = ""
        ):
        """
            Template function for the second screen layout with a barplot of
            historical data.

            Arguments:
            ----------
                current_value: float
                    Current value to display
                logger: Logger
                    Logger instance to retrieve historical data for the barplot
                unit: str
                    Unit of the current value to display (e.g. "°C", "%", "ppm")
                title: str
                    Title to display above the barplot
            
            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
    #-- Get frame buffer ----------------------------------------------
        fb = self.screen_writer.fb #.......................... Get the frame buffer from the screen writer

    #-- Set Font ------------------------------------------------------
        self.screen_writer.change_font(OpenSansBold_20)  #.... Change the font back to the default for the next screen

    #-- Clear frame buffer with white color ---------------------------
        self.screen_writer.clear_fb(color=0xFF)

    #-- Plot title ----------------------------------------------------
        self.screen_writer.add_text(
                text = title,
                x = 10,
                y = 5,
                invert = True
            )

    #-- Plot barplot --------------------------------------------------
        RECT_START_X  = 10 #....................... Start x coordinate of the barplot area
        RECT_END_X    = 264 - 50 #................. End x coordinate of the barplot area
        RECT_START_Y  = 30 #....................... Start y coordinate of the barplot area
        RECT_HEIGHT   = 55 #....................... Height of the barplot area

        if logger.count() > 0:
        #-- Get the minimal and maximal value -------------------------
            value_min = logger.min()
            value_max = logger.max()
        #-- Correct by the current value ------------------------------
            if current_value < value_min:
                value_min = current_value
            if current_value > value_max:
                value_max = current_value
        #-- Set logical x/y ranges for the barplot --------------------
            x_min = 0 #............................ Set x_min to 0 seconds ago (current time)
            x_max = logger.max_bin_history_sec()#.. Set x_max to 24 hours in seconds
            y_min = value_min - 2. #............... Set y_min to the minimum logged temperature minus some margin
            y_max = value_max + 2. #............... Set y_max to the maximum logged temperature plus some margin

            x_scr_min = RECT_START_X
            y_scr_min = RECT_START_Y
            x_scr_max = RECT_END_X
            y_scr_max = RECT_START_Y + RECT_HEIGHT

            samples = logger.bin_series() #........ Binned samples for the barplot

            self.draw_barplot(
                    x_scr_min,
                    y_scr_min,
                    x_scr_max,
                    y_scr_max,
                    x_min,
                    y_min,
                    x_max,
                    y_max,
                    samples,
                    color=0x00
                ) #................................ Draw the barplot
            
        #-- Plot y values on the right side of the barplot ------------
            self.screen_writer.change_font(OpenSansBold_12)  #.... Change the font to small size
            self.screen_writer.add_text(
                text = f"{y_max:2.1f}",
                x = int(RECT_END_X + 5),
                y = int(RECT_START_Y),
                invert = True
            )
            self.screen_writer.add_text(
                text = f"{y_min:2.1f}",
                x = int(RECT_END_X + 5),
                y = int(RECT_START_Y + 0.90 * RECT_HEIGHT),
                invert = True
            )
            self.screen_writer.change_font(OpenSansBold_20)  #.... Change the font back to the default for the next screen

    #-- Draw box around the barplot -----------------------------------
        fb.rect(
            RECT_START_X,
            RECT_START_Y,
            RECT_END_X - RECT_START_X,
            RECT_HEIGHT,
            0x00,
            False
        ) #............................................. Draw first rectangle for temperature

    #-- Draw ticks and labels for the barplot -------------------------
        fb.vline(
            int(RECT_START_X),
            int(RECT_START_Y + RECT_HEIGHT - 0),
            5,
            0x00
        ) #... Y-axis line

        fb.vline(
            int(RECT_START_X + 0.25 * (RECT_END_X - RECT_START_X)),
            int(RECT_START_Y + RECT_HEIGHT - 0),
            5,
            0x00
        ) #... Y-axis line

        fb.vline(
            int(RECT_START_X + 0.5 * (RECT_END_X - RECT_START_X)),
            int(RECT_START_Y + RECT_HEIGHT - 0),
            5,
            0x00
        ) #... Y-axis line

        fb.vline(
            int(RECT_START_X + 0.75 * (RECT_END_X - RECT_START_X)),
            int(RECT_START_Y + RECT_HEIGHT - 0),
            5,
            0x00
        ) #... Y-axis line

        fb.vline(
            int(RECT_END_X - 1),
            int(RECT_START_Y + RECT_HEIGHT - 0),
            5,
            0x00
        ) #... Y-axis line

        self.screen_writer.change_font(OpenSansBold_12)  #.... Change the font to small size

        self.screen_writer.add_text(
                text = "24h",
                x = int(RECT_START_X),
                y = int(RECT_START_Y + RECT_HEIGHT + 5),
                invert = True
            )

        self.screen_writer.add_text(
                text = "18h",
                x = int(RECT_START_X + 0.25 * (RECT_END_X - RECT_START_X)),
                y = int(RECT_START_Y + RECT_HEIGHT + 5),
                invert = True
            )

        self.screen_writer.add_text(
                text = "12h",
                x = int(RECT_START_X + 0.5 * (RECT_END_X - RECT_START_X)),
                y = int(RECT_START_Y + RECT_HEIGHT + 5),
                invert = True
            )

        self.screen_writer.add_text(
                text = "6h",
                x = int(RECT_START_X + 0.75 * (RECT_END_X - RECT_START_X)),
                y = int(RECT_START_Y + RECT_HEIGHT + 5),
                invert = True
            )

        self.screen_writer.add_text(
                text = "Now",
                x = int(RECT_START_X + 0.90 * (RECT_END_X - RECT_START_X)),
                y = int(RECT_START_Y + RECT_HEIGHT + 5),
                invert = True
            )

        self.screen_writer.change_font(OpenSansBold_20)  #.... Change the font back to the default for the next screen

    #-- Add information -----------------------------------------------
        self.screen_writer.add_text(
                text = f"Current: {current_value:2.1f} {unit}",
                x = 10,
                y = 110,
                invert = True
            )
        
        if logger.count() > 0:
        #-- Get the minimal and maximal value -------------------------
            value_min = logger.min()
            value_max = logger.max()
        #-- Corect by the current value -------------------------------
            if current_value < value_min:
                value_min = current_value
            if current_value > value_max:
                value_max = current_value
        #-- Plot text -------------------------------------------------
            separator = "/" if unit == "hPa" else " / " #.... Keep four-digit pressure values and their unit on one line
            self.screen_writer.add_text(
                    text = f"Min/Max: {value_min:2.1f}{separator}{value_max:2.1f} {unit}",
                    x = 10,
                    y = 140,
                    invert = True
                )
        else:
            self.screen_writer.add_text(
                    text = f"Min/Max: n/a {unit}",
                    x = 10,
                    y = 140,
                    invert = True
                )

    #-- Return --------------------------------------------------------
        return
    
    def draw_barplot(
            self,
            x_scr_min, y_scr_min,
            x_scr_max, y_scr_max,
            x_min, y_min,
            x_max, y_max,
            samples,
            color=0x00
        ):
        """
        Draw a barplot in screen coords (x_scr_min/y_scr_min) - (x_scr_max/y_scr_max),
        where x/y are linearly mapped from logical ranges [x_min,x_max] and
        [y_min,y_max]. Samples is list of (x_value, y_value). Bars are stretched
        accordingly and separated by a 1px white line. Values outside the
        [y_min,y_max] logical range are cropped to the physical box.
        """
        fb = self.screen_writer.fb #...................................... Get the frame buffer from the screen writer
        #samples = samples[::-1] #........................................ Reverse the samples to have the most recent one at the end of the list


    #-- Invert bar along x-axis ----------------------------------------------
        x_min = -x_max
        x_max =  0.
        samples = [(-x, y) for (x, y) in samples] #..... Invert x values to have 0 at the right and positive values to the left

    #-- Functions to map logical x/y values to screen coordinates --------------------------------------
        def _map_x_value(x_value):
            # Map logical x value to screen x coordinate
            if x_value < x_min:
                return x_scr_min
            elif x_value > x_max:
                return x_scr_max
            else:
                return int(x_scr_min + (x_value - x_min) / (x_max - x_min) * (x_scr_max - x_scr_min))
            
        def _map_y_value(y_value):
            # Map logical y value to screen y coordinate (inverted)
            if y_value < y_min:
                return y_scr_max
            elif y_value > y_max:
                return y_scr_min
            else:
                return int(y_scr_max - (y_value - y_min) / (y_max - y_min) * (y_scr_max - y_scr_min))
            
    #-- Iterate over samples and plot bars -------------------------------------------------------------
        for k in range(len(samples)):
        #-- Select physical x values for the left and right edge of the bar ----------------------------
            if k < 1:
                x_value_left = 0 #................. For the first bar, we can set the left edge to the start of the x range
            else:
                x_value_left = samples[k-1][0] #... Phsyical x value in seconds ago for the left edge of the bar (previous sample)
            x_value_right = samples[k][0] #........ Phsyical x value in seconds ago for the right edge of the bar (current sample)

        #-- Select physical y value of the bar ---------------------------------------------------------
            y_value = samples[k][1] #.............. Physical y value in the given units for the current sample
        
        #-- Convert logical x/y values to screen coordinates for the bar edges -------------------------
            x_bar_left   = _map_x_value(x_value_left) #.. Map logical x to screen x for the left edge of the bar
            x_bar_right  = _map_x_value(x_value_right) #. Map logical x to screen x for the left edge of the bar
            y_bar        = _map_y_value(y_value) #....... Map logical y to screen y for the top of the bar (inverted because screen y increases downwards)

        #-- Draw filled bar as a rectangle -------------------------------------------------------------
            fb.rect(
                x_bar_left,
                y_bar,
                x_bar_right-x_bar_left,
                y_scr_max - y_bar,
                color,
                True
            )
        
        #-- Plot white vertical bars to separate the bars ------------------------------------------------
            fb.vline(x_bar_right, y_scr_min, y_scr_max, 0xFF)
            fb.vline(x_bar_left, y_scr_min, y_scr_max, 0xFF)

    #-- Plot 5 bars ---------------------------------------------------
        N = 5
        dY = (y_scr_max - y_scr_min) / N
        for i in range(N + 1):
            y = int(y_scr_min + i * dY)
            fb.hline(x_scr_min, y, x_scr_max - x_scr_min + 1, 0xFF)

    #-- Return -----------------------------------------------------------------------------------------
        return

# + ==================================================================== +
# |                   TESTING AND EXAMPLE USAGE BELOW                    |
# + ==================================================================== +

if __name__ == "__main__":

#-- Initialize Display-driver (and frame buffer) ------------------------
    epd = EPD_2in7_V2() #....... Init Display-Treiber (inkl. FrameBuffer)

#-- Initialize the writer for portrait framebuffer ----------------------
    sw = ScreenWriter(
                screen_driver = epd,
                font = OpenSansBold_28,
                verbose = True
            )
    
#-- Initialize the screen manager with the screen writer ----------------
    sm = ScreenManager(screen_writer=sw)

#-- Draw the first screen layout with example data ----------------------
    sm.screen1(temp=22.5, hum=45.0, pressure=1013.25, CO2=400.0)

