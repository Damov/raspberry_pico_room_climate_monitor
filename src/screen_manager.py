import machine
from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_writer import ScreenWriter

from fonts import OpenSansBold_12, OpenSansBold_20, OpenSansBold_28 #..... Load fonts

class ScreenManager:
    """
        Draws the screen with actual data onto the e-ink display. It
        manages the different screen layouts and their updates.
    """
    def __init__(self, screen_writer):
    #-- Save attributes -----------------------------------------------
        self.screen_writer = screen_writer
    
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
            Draws the first screen layout with the given data.

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
                    for the pressure
                logger_humidity_shortterm: Logger
                    Logger instance to retrieve historical data 
                    for the humidity
                logger_co2_shortterm: Logger
                    Logger instance to retrieve historical data 
                    for the CO2
            
            Returns:
            --------
                None
                   This function draws the screen and does not return any value.
        """
    #-- Set Font ------------------------------------------------------
        self.screen_writer.change_font(OpenSansBold_28)  #............ Change the font back to the default for the next screen

    #-- Clear frame buffer with white color ---------------------------
        self.screen_writer.clear_fb(color=0x00)

    #-- Load screen 1 background --------------------------------------
        img_width, img_height = 264, 176  # set to image size
        
        with open("img/static_screen1_background.bin", "rb") as f:
            img_buf = bytearray(f.read())
        
        self.screen_writer.add_image(
                img_buf,
                img_width,
                img_height,
                x=0,
                y=0
            )
    
    #-- Add temperature -----------------------------------------------
        self.screen_writer.add_text(
                text = f"{temp:2.1f} °C",
                x = 145,
                y = 15,
                invert = True
            )

    #-- Add humidity --------------------------------------------------
        self.screen_writer.add_text(
                text = f"{hum:2.1f} %",
                x = 145,
                y = 70,
                invert = True
            )

    #-- Add CO2 --------------------------------------------------------
        self.screen_writer.add_text(
                text = f"{CO2:4.0f} ppm",
                x = 145,
                y = 120,
                invert = True
            )
        
    #-- Add assesment of air quaility ---------------------------------
        """
            - green (good): 400–800 ppm
            - yellow (medium): 800–1200 ppm
            - orange (bad): 1200–2000 ppm
            - red (very bad/alarm): >2000 ppm
        """
        self.screen_writer.change_font(OpenSansBold_20)
        if CO2 < 800:
            text = "Good"
        elif CO2 < 1200:
            text = "Medium"
        elif CO2 < 2000:
            text = "Bad"
        else:
            text = "Very Bad"
        
        self.screen_writer.add_text(
                text = text,
                x = 145,
                y = 150,
                invert = True
            )
        self.screen_writer.change_font(OpenSansBold_28) #............ Change the font back to the default for the next screen

    #-- Add barplot of historical temperature data --------------------
        x_min = 0
        y_min = 0
        x_max = 0.25 * 3600
        y_max = 40

        x_scr_min = 5
        y_scr_min = 5
        x_scr_max = 120
        y_scr_max = 53

        samples = logger_temperature_shortterm.bin_series()

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
            )
        
    #-- Add barplot of historical humidity data --------------------
        x_min = 0
        y_min = 20
        x_max = 0.25 * 3600
        y_max = 100

        x_scr_min = 5
        y_scr_min = 60
        x_scr_max = 120
        y_scr_max = 108

        samples = logger_humidity_shortterm.bin_series()

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
            )

    #-- Add barplot of historical CO2 data -------------------------
        x_min = 0
        y_min = 400
        x_max = 0.25 * 3600
        y_max = 2500

        x_scr_min = 5
        y_scr_min = 118
        x_scr_max = 120
        y_scr_max = 166

        samples = logger_co2_shortterm.bin_series()

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
            )

    #-- Return --------------------------------------------------------
        return


    def screen2_temperature(
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
                text = f"{y_max:2.1f} {unit}",
                x = int(RECT_END_X + 5),
                y = int(RECT_START_Y),
                invert = True
            )
            self.screen_writer.add_text(
                text = f"{y_min:2.1f} {unit}",
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
            self.screen_writer.add_text(
                    text = f"Min/Max: {value_min:2.1f} / {value_max:2.1f} {unit}",
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

