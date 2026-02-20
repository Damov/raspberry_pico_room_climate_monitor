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

    def add_image(self, img_buf, img_w, img_h, x=0, y=0):
        """
        Add an image to the framebuffer. The image is provided as a bytearray
        (img_buf) with the specified width (img_w) and height (img_h).

        Arguments:
        ----------
        img_buf: bytearray
          The image data as a bytearray, where each byte represents a pixel color.
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

        Returns:
        --------
        None
        """
    #-- Loop through each pixel in the image buffer and draw it on the framebuffer -
        for yy in range(img_h):
            dy = y + yy
            if dy < 0 or dy >= self.height:
                continue
            row_off = yy * img_w
            for xx in range(img_w):
                dx = x + xx
                if dx < 0 or dx >= self.width:
                    continue
                c = img_buf[row_off + xx]
                self.fb.pixel(dx, dy, c)
    #-- Return -----------------------------------------------------------------
        return

    def add_image_center(
                    self,
                    img_buf,
                    img_w,
                    img_h,
                    x_start=0,
                    x_end=None,
                    y_start=0,
                    y_end=None
                ):
        """
            Draw an image centered horizontally and vertically within a
            defined rectangle.

            Arguments:
            ----------
            img_buf: bytearray
              The image data as a bytearray, where each byte represents
              a pixel color.
            img_w: int
              The width of the image in pixels.
            img_h: int
              The height of the image in pixels.
            x_start: int
              The starting x-coordinate of the rectangle (default: 0).
            x_end: int or None
              The ending x-coordinate of the rectangle (default: None,
              which means the width of the screen).
            y_start: int
              The starting y-coordinate of the rectangle (default: 0).
            y_end: int or None
              The ending y-coordinate of the rectangle (default: None,
              which means the height of the screen).

            Returns:
            --------
            None
        """
    #-- Set default values for x_end and y_end if they are None -----------------
        if x_end is None:
            x_end = self.width
        if y_end is None:
            y_end = self.height

    #-- Calculate the position to center the image within the defined rectangle -
        area_w = x_end - x_start
        area_h = y_end - y_start

        x = x_start + (area_w - img_w) // 2
        y = y_start + (area_h - img_h) // 2

    #-- Add the image at the calculated position --------------------------------
        self.add_image(img_buf, img_w, img_h, x, y)

    #-- Return ------------------------------------------------------------------
        return

    def add_image_horizontal_center(
                            self,
                            img_buf,
                            img_w,
                            img_h,
                            y,
                            x_start=0,
                            x_end=None
                        ):
        """
            Draw an image centered horizontally within a defined
            horizontal area, with a fixed y-coordinate.

            Arguments:
            ----------
            img_buf: bytearray
              The image data as a bytearray, where each byte represents
              a pixel color.
            img_w: int
              The width of the image in pixels.
            img_h: int
              The height of the image in pixels.
            y: int
              The y-coordinate (row) for the top-left corner of the image.
            x_start: int
              The starting x-coordinate of the horizontal area (default: 0).
            x_end: int or None
              The ending x-coordinate of the horizontal area (default: None,
              which means the width of the screen).

            Returns:
            --------
            None
        """
    #-- Set default value for x_end if it is None ---------------------------
        if x_end is None:
            x_end = self.width
    
    #-- Calculate the x position to center the image horizontally -----------
        area_w = x_end - x_start
        x = x_start + (area_w - img_w) // 2

    #-- Add the image at the calculated position ----------------------------
        self.add_image(img_buf, img_w, img_h, x, y)

    #-- Return --------------------------------------------------------------
        return

    def add_image_vertical_center(
                            self,
                            img_buf,
                            img_w,
                            img_h,
                            x,
                            y_start=0,
                            y_end=None
                        ):
        """
            Draw an image centered vertically within a defined vertical area,
            with a fixed x-coordinate.

            Arguments:
            ----------
            img_buf: bytearray
              The image data as a bytearray, where each byte represents
              a pixel color.
            img_w: int
              The width of the image in pixels.
            img_h: int
              The height of the image in pixels.
            x: int
              The x-coordinate (column) for the top-left corner of the image.
            y_start: int
              The starting y-coordinate of the vertical area (default: 0).
            y_end: int or None
              The ending y-coordinate of the vertical area (default: None,
              which means the height of the screen).

            Returns:
            --------
            None
        """
    #-- Set default value for y_end if it is None ---------------------------
        if y_end is None:
            y_end = self.height

    #-- Calculate the y position to center the image vertically -------------
        area_h = y_end - y_start
        y = y_start + (area_h - img_h) // 2

    #-- Add the image at the calculated position ----------------------------
        self.add_image(img_buf, img_w, img_h, x, y)

    #-- Return --------------------------------------------------------------
        return
    
    # + =================================================================== +
    # |                   HIGH-LEVEL DISPLAY FUNCTIONS                      |
    # + =================================================================== +

    def show(self):
        """
            Display the buffer on the physical display if a screen driver is available.
        """
    #-- Set mode to landscape --------------------------------------------------
        mode="landscape" #... (Quick workaround for showing only landscape buffer of EPD_2in7_V2 driver)
        
    #-- Try to guess the buffer behind fb ------------------------------------------------------------
        buf = None

    #-- Typical Waveshare 2.7" case: check for known buffer attributes based on the framebuffer used -
        if hasattr(self.screen, "buffer_1Gray_Portrait") and self.fb is self.screen.image1Gray_Portrait:
            buf = self.screen.buffer_1Gray_Portrait
        elif hasattr(self.screen, "buffer_1Gray_Landscape") and self.fb is self.screen.image1Gray_Landscape:
            buf = self.screen.buffer_1Gray_Landscape
        elif hasattr(self.screen, "buffer_4Gray") and self.fb is self.screen.image4Gray:
            buf = self.screen.buffer_4Gray

    #-- If we couldn't guess the buffer, fall back to using the framebuffer's buffer if it exists ----
        if mode == "fast" and hasattr(self.screen, "display_Fast"):
            self.screen.display_Fast(buf)
        elif mode == "base" and hasattr(self.screen, "display_Base"):
            self.screen.display_Base(buf)
        elif mode == "landscape" and hasattr(self.screen, "display_Landscape"):
            self.screen.display_Landscape(buf)
        elif mode == "partial" and hasattr(self.screen, "display_Partial"):
            self.screen.display_Partial(buf)
        elif mode == "4gray" and hasattr(self.screen, "display_4Gray"):
            self.screen.display_4Gray(buf)
        elif hasattr(self.screen, "display"):
            self.screen.display(buf)
    #-- Else: screen can have its own refresh() method -----------------------------------------------
        elif hasattr(self.screen, "refresh"):
            self.screen.refresh()

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

