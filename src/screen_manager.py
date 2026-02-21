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
    
    def screen1(self, temp, hum, pressure, CO2):
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
                text = f"{CO2:3.0f} ppm",
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

