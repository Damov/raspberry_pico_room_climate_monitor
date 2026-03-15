# screen_writer.py

# =====================================================================
# TODO:
# - Add more high-level text functions (e.g. line between two points,
#   rectangle, etc.)
# =====================================================================

import framebuf
from third_party_lib.writer import Writer
from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2


class FBDevice(framebuf.FrameBuffer):
    """
    FrameBuffer subclass with width/height attributes,
    suitable as 'device' for Writer.
    """
    def __init__(self, buf, width, height, fmt):
    #-- Store public attrs for Writer -------------------
        self.width = width
        self.height = height
    #-- Initialise the base FrameBuffer -----------------
        super().__init__(buf, width, height, fmt)
    #-- Return ------------------------------------------
        return

class ScreenWriter:
    """
    High-level helper functions for drawing text and images on a
    framebuffer of a physical display driver for showing the buffer
    on the display and putting the display to sleep.

    The module is derived from Frederik Andersen's EasyWriter module
    (https://github.com/frederik-andersen/micropython-ePaperWeatherStation),
    but extended with additional features and optimizations for better
    performance and ease of use with the employed Waveshare 2.7-inch e-paper
    display drivers.
    """

    def __init__(
            self,
            screen_driver,
            font,
            verbose=True
        ):
        """
        Arguments:
        ----------
        screen_driver: EPD_2in7_V2 instance
             The display driver instance that provides framebuffers and
             display/sleep methods.
        font: font module
            The font module to use with Writer module.
        verbose: bool
            Verbose output during initialization (default: True).

        Returns:
        --------
            None
        """
    #-- Validate the input -----------------------------------------------------
        if not isinstance(screen_driver, EPD_2in7_V2):
            raise ValueError("screen_driver must be an instance of EPD_2in7_V2")
    
    #-- Store the screen driver for later use (e.g. for show() and sleep()) ----
        self.screen = screen_driver

    #-- Choose which physical framebuffer to use (landscape) -------------------
        self.fb = screen_driver.image1Gray_Landscape  # this is a FrameBuffer

    #-- Store width and height for Writer --------------------------------------
        self.width = screen_driver.height
        self.height = screen_driver.width
    
    #-- Create a FBDevice instance as the Writer "device" ----------------------
        self.device = FBDevice(
                            self.fb,
                            self.width,
                            self.height,
                            framebuf.MONO_VLSB
                        )  # match image1Gray_Landscape format
    #-- Initialize writer ------------------------------------------------------
        self.writer = Writer(self.device, font, verbose=verbose)

    #-- Return -----------------------------------------------------------------
        return
    
    # + =================================================================== +
    # |                   HIGH-LEVEL TEXT FUNCTIONS                         |
    # + =================================================================== +
    
    def change_font(self, font):
        """
            Change the font used by the writer.

            Arguments:
            ----------
            font: any?
              The new font module to use with Writer/CWriter.

            Returns:
            --------
            None
        """
        self.writer.font = font
        return

    def set_textpos(self, row, col):
        """
            Set text cursor position (row = y, col = x).

            Arguments:
            ----------
            row: int
              The row (y-coordinate) to set the text cursor to.
            col: int
              The column (x-coordinate) to set the text cursor to.

            Returns:
            --------
            None
        """
        self.writer.set_textpos(self.device, row, col)
        return
    
    def add_text(self, text, x, y, invert=True):
        """
            Adds text at the specified (x, y) position. The
            (x, y) coordinates represent the top-left corner
            of the first character.

            Arguments:
            ----------
            text: str
              The string of text to add.
            x: int
              The x-coordinate (column) for the top-left corner of the text.
            y: int
              The y-coordinate (row) for the top-left corner of the text.
            invert: bool
              If True, the text will be drawn in inverted colors (default: True).

            Returns:
            --------
            None
        """
        self.writer.set_textpos(self.device, y, x)
        self.writer.printstring(text, invert=invert)
        return

    def add_text_center(
                self,
                text,
                x_start=0,
                x_end=None,
                y_start=0,
                y_end=None,
                invert=True
            ):
        """
            Write text centered horizontally and vertically within a defined
            rectangle.

            Arguments:
            ----------
            text: str
              The string of text to add.
            x_start: int
              The starting x-coordinate of the rectangle (default: 0).
            x_end: int or None
              The ending x-coordinate of the rectangle (default: None, which means the width of the screen).
            y_start: int
              The starting y-coordinate of the rectangle (default: 0).
            y_end: int or None
              The ending y-coordinate of the rectangle (default: None, which means the height of the screen).
            invert: bool
              If True, the text will be drawn in inverted colors (default: True).

            Returns:
            --------
            None
        """
    #-- Set default values for x_end and y_end if they are None ----------------
        if x_end is None:
            x_end = self.width
        if y_end is None:
            y_end = self.height

    #-- Calculate the position to center the text within the defined rectangle -
        font_h = self.writer.font.height()
        area_h = y_end - y_start
        y = y_start + (area_h - font_h) // 2

        text_w = self.writer.stringlen(text)
        area_w = x_end - x_start
        x = x_start + (area_w - text_w) // 2
    
    #-- Add the text at the calculated position --------------------------------
        self.add_text(text, x, y, invert=invert)
    
    #-- Return -----------------------------------------------------------------
        return

    def add_text_horizontal_center(
                            self,
                            text,
                            y,
                            x_start=0,
                            x_end=None,
                            invert=True
                        ):
        """
            Add text centered horizontally within a defined horizontal area, with
            a fixed y-coordinate.

            Arguments:
            ----------
            text: str
              The string of text to add.
            y: int
              The y-coordinate (row) for the top-left corner of the text.
            x_start: int
              The starting x-coordinate of the horizontal area (default: 0).
            x_end: int or None
              The ending x-coordinate of the horizontal area (default: None, which means the width of the screen).
            invert: bool
              If True, the text will be drawn in inverted colors (default: True).

            Returns:
            --------
            None
        """
    #-- Set default value for x_end if it is None --------------------------------
        if x_end is None:
            x_end = self.width

    #-- Calculate the x position to center the text horizontally -----------------
        text_w = self.writer.stringlen(text)
        area_w = x_end - x_start
        x = x_start + (area_w - text_w) // 2

    #-- Add the text at the calculated position ----------------------------------
        self.add_text(text, x, y, invert=invert)

    #-- Return -------------------------------------------------------------------
        return

    def add_text_vertical_center(
                            self,
                            text,
                            x,
                            y_start=0,
                            y_end=None,
                            invert=True
                        ):
        """
            Add text centered vertically within a defined vertical area, with a
            fixed x-coordinate.

            Arguments:
            ----------
            text: str
              The string of text to add.
            x: int
              The x-coordinate (column) for the top-left corner of the text.
            y_start: int
              The starting y-coordinate of the vertical area (default: 0).
            y_end: int or None
              The ending y-coordinate of the vertical area (default: None, which
              means the height of the screen).
            invert: bool
              If True, the text will be drawn in inverted colors (default: True).

            Returns:
            --------
            None
        """
    #-- Set default value for y_end if it is None --------------------------------
        if y_end is None:
            y_end = self.height

    #-- Calculate the y position to center the text vertically -------------------
        font_h = self.writer.font.height()
        area_h = y_end - y_start
        y = y_start + (area_h - font_h) // 2

    #-- Add the text at the calculated position ----------------------------------
        self.add_text(text, x, y, invert=invert)

    #-- Return -------------------------------------------------------------------
        return

    # + =================================================================== +
    # |                   HIGH-LEVEL IMAGE FUNCTIONS                        |
    # + =================================================================== +

    def add_image(
              self,
              fname,
              img_w,
              img_h,
              x = 0,
              y = 0,
              do_gc = True,
              show_after = True,
              invert_colors = True
            ):
        """
        Add an image to the framebuffer. The image is provided as a bytearray
        (img_buf) with the specified width (img_w) and height (img_h).

        Arguments:
        ----------
        fname: str
          The path to the image file to be added.
        img_w: int
          The width of the image in pixels.
        img_h: int
          The height of the image in pixels.
        x: int
          The x-coordinate (column) for the top-left corner of the image on the
          framebuffer (default: 0).
        y: int
          The y-coordinate (row) for the top-left corner of the image on the
          framebuffer (default: 0).
        do_gc: bool
          If True, perform garbage collection after drawing the image to free up
          memory (default: True).
        show_after: bool
          If True, call self.show() to update the display after drawing the image
          (default: True).
        invert_colors: bool
          If True, invert the colors of the image when drawing (default: True).

        Returns:
        --------
        None
        """

    #-- Garbage collection to free up memory after drawing the image -----------
        if do_gc:
            import gc
            gc.collect()

    #-- Read the image file in chunks and draw it on the framebuffer to avoid
    #   loading the entire image into memory at once ---------------------------
        row_bytes = img_w #..................................... 1 byte per pixel
        line_buf = bytearray(row_bytes) #....................... Buffer for one row of pixel data

        with open(fname, "rb") as f:
            for yy in range(img_h):
                dy = y + yy
                n = f.readinto(line_buf)
                if n != row_bytes:
                    break #...................................... Truncated
                
                if dy < 0 or dy >= self.height:
                    continue #................................... Skip rows outside the framebuffer bounds
                
                for xx in range(img_w):
                    dx = x + xx
                    if dx < 0 or dx >= self.width:
                        continue #............................... Skip pixels outside the framebuffer bounds

                #-- Map the pixel value from the image buffer to the framebuffer
                #   color ------------------------------------------------------
                    v = line_buf[xx] #........................... Get pixel value from image buffer (0-255)
                    if invert_colors:
                        c = 0 if v > 127 else 1 #................ Invert color: 1 for dark pixels, 0 for light pixels
                    else:
                        c = 1 if v > 127 else 0 #................ No inversion: 1 for light pixels, 0 for dark pixels
                    self.fb.pixel(dx, dy, c) #................... Draw pixel on framebuffer
    #-- Show the updated framebuffer on the display if requested ---------------
        if show_after:
            self.show()

    #-- Return -----------------------------------------------------------------
        return
    
    # + =================================================================== +
    # |                   HIGH-LEVEL DISPLAY FUNCTIONS                      |
    # + =================================================================== +

    def show(self):
        """
            Display the buffer on the physical display with full update of
            the screen.
        """
        buf = self.screen.buffer_1Gray_Landscape
        self.screen.display_Landscape(buf)

    #-- Return ---------------------------------------------------------------------------------------
        return

    def show_fast(self):
        """
            Display the buffer on the physical display with a fast update of
            the screen.
        """
        buf = self.screen.buffer_1Gray_Landscape
        self.screen.display_Landscape_Fast(buf)

    #-- Return ---------------------------------------------------------------------------------------
        return

    def show_partial(self):
        """
            Display the buffer on the physical display with a partial update
            of the screen.
        """
        buf = self.screen.buffer_1Gray_Landscape
        self.screen.display_Landscape_Partial(buf)

    #-- Return ---------------------------------------------------------------------------------------
        return
    
    def clear_fb(self, color=0xFF):
        """
            Clears the framebuffer and overwrites it completely with a specified
            color.

            Arguments:
            ----------
            color: int or hex
              The color to fill the framebuffer with (default: 0xFF, which is white
              for monochrome displays).

            Returns:
            --------
            None
        """
        self.fb.fill(color)
        return

    def sleep(self):
        """
            Put the physical display to sleep if a screen driver is available and
            supports it.

            Notes:
            - If screen is only a FrameBuffer, there is nothing to do.
            - Attempts to call sleep() or Sleep() method on the screen driver if
              it exists.
        """
    #-- If the screen is just the FrameBuffer, there is nothing to do ------------
        if self.screen is self.fb:
            return
        
    #-- Try to call sleep() or Sleep() method on the screen driver if it exists --
        if hasattr(self.screen, "sleep"):
            self.screen.sleep()

    #-- Some drivers might use capitalized Sleep() method instead of sleep() -----
        elif hasattr(self.screen, "Sleep"):
            self.screen.Sleep()
    
    #-- Return -------------------------------------------------------------------
        return


# + ==================================================================== +
# |                   TESTING AND EXAMPLE USAGE BELOW                    |
# + ==================================================================== +

if __name__ == "__main__":
    from fonts import OpenSansBold_20 #............ Load example font

#-- Initialize Display-driver (and frame buffer) ------------------------
    epd = EPD_2in7_V2() #.......................... Init Display-Treiber (inkl. FrameBuffer)

#-- Initialize the writer for portrait framebuffer ----------------------
    sw = ScreenWriter(
                screen_driver = epd,
                font = OpenSansBold_20,
                verbose = True
            )
#-- Clear frame buffer with white color ---------------------------------
    sw.clear_fb(color=epd.white)

#-- Add some text at the center -----------------------------------------
    sw.add_text_center("Hello 2.7\"")

#-- Show the buffer in fast mode -----------------------------------------
    sw.show()

#-- Put the display to sleep ---------------------------------------------
    sw.sleep()

