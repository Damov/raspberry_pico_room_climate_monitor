import machine
from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2
from screen_writer import ScreenWriter

from fonts import OpenSansBold_20, OpenSansBold_28 #..... Load fonts

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
    
    def screen1(self, temp, hum, pressure, CO2, logger):
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
                logger: Logger
                    Logger instance to retrieve historical data 
                    for the barplot
            
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

        samples = logger.get_temperature()

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

        samples = logger.get_humidity()

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

        samples = logger.get_co2()

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
        fb = self.screen_writer.fb

    #-- Invert bar along x-axis ----------------------------------------------
        x_min = -x_max
        x_max =  0.
        samples = [(-x, y) for (x, y) in samples] #..... Invert x values to have 0 at the right and positive values to the left
    
    #-- Get dT and compute dX of a bar ---------------------------------------
        bar_dT = samples[0][0] #......................................... dT
        if bar_dT <= 0:
            bar_dT = -bar_dT
        bar_dX = (x_scr_max - x_scr_min) / (x_max - x_min) * bar_dT  #... dX in screen coords for the given dT
        bar_dX = int(bar_dX) + 2 #....................................... Convert to int and leave 1px for white separator between bars

    #-- Iterate over samples and plot bars -----------------------------------
        def map_x_value(x_value):
            # Map logical x value to screen x coordinate
            if x_value < x_min:
                return x_scr_min
            elif x_value > x_max:
                return x_scr_max
            else:
                return int(x_scr_min + (x_value - x_min) / (x_max - x_min) * (x_scr_max - x_scr_min))
        def map_y_value(y_value):
            # Map logical y value to screen y coordinate (inverted)
            if y_value < y_min:
                return y_scr_max
            elif y_value > y_max:
                return y_scr_min
            else:
                return int(y_scr_max - (y_value - y_min) / (y_max - y_min) * (y_scr_max - y_scr_min))
        
        for sample in samples:
            x_value = sample[0] #....................... Phsyical x value in seconds ago
            y_value = sample[1] #....................... Physical y value in the given units

            x_bar_start = map_x_value(x_value) #........ Map logical x to screen x for the left edge of the bar
            x_bar_end   = x_bar_start + bar_dX #........ Right edge of the bar is start + bar width in screen coords
            y_bar_top   = map_y_value(y_value) #........ Map logical y to screen y for the top of the bar (inverted because screen y increases downwards)
            y_bar_bottom = y_scr_max #.................. Bottom of the bar is at y_scr_max

            # Draw filled bar
            for x in range(x_bar_start, x_bar_end + 1):
                fb.vline(x, y_bar_top, y_bar_bottom - y_bar_top + 1, color)

    #-- Plot white vertical bars --------------------------------------
        for sample in samples:
            x_value = sample[0] #....................... Phsyical x value in seconds ago
            x_bar_start = map_x_value(x_value) #........ Map logical x to screen x for the left edge of the bar
            fb.vline(
                x_bar_start,
                y_scr_min,
                y_scr_max - y_scr_min + 1,
                0xFF
            )

    #-- Plot 5 bars ---------------------------------------------------
        N = 5
        dY = (y_scr_max - y_scr_min) / N
        for i in range(N + 1):
            y = int(y_scr_min + i * dY)
            fb.hline(x_scr_min, y, x_scr_max - x_scr_min + 1, 0xFF)

    #-- Draw white rectangle around the barplot -----------------------
        """
        fb.rect(
            x_scr_min,
            y_scr_min,
            x_scr_max - x_scr_min + 1,
            y_scr_max - y_scr_min + 1,
            0xFF
        )
        """

    #-- Return --------------------------------------------------------
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

