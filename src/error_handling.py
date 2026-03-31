"""
=============================================================================
error_handling.py

Error handling for the e-ink display. It provides functions for displaying
exceptions on the screen and logging them to a file.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

def show_exception_on_screen(e, show_traceback=False):
    """
        Display an exception on the e-paper display in landscape mode
        using a full refresh.


        Arguments:
        ----------
        e : Exception
            The exception object to be displayed on the screen.
        show_traceback : bool
            If True, display the wrapped full traceback.
            If False, display only the exception description and
            the last known file/line location where the error occurred.


        Returns:
        --------
            None
    """

#-- Import required modules and free memory -------------------------
    import gc, sys, io
    gc.collect()

#-- Helper: wrap text into multiple display lines -------------------
    def wrap_text(text, max_chars):
        """
            Wrap a string into multiple lines.
            Existing line breaks are preserved.
            Long words are split if necessary.
        """
        wrapped_lines = []

        for raw_line in text.split("\n"):
            line = raw_line.strip()

            if not line:
                wrapped_lines.append("")
                continue

            current = ""
            words = line.split(" ")

            for word in words:
                # Split very long words into chunks
                if len(word) > max_chars:
                    if current:
                        wrapped_lines.append(current)
                        current = ""

                    while len(word) > max_chars:
                        wrapped_lines.append(word[:max_chars])
                        word = word[max_chars:]

                    if word:
                        current = word
                    continue

                # Append word if it still fits
                if not current:
                    current = word
                elif len(current) + 1 + len(word) <= max_chars:
                    current += " " + word
                else:
                    wrapped_lines.append(current)
                    current = word

            if current:
                wrapped_lines.append(current)

        return wrapped_lines


#-- Capture traceback into a string buffer --------------------------
    buf = io.StringIO()  #........................ Create a string buffer for traceback capture
    sys.print_exception(e, buf)  #................ Write the exception and traceback into the buffer
    tb_str = buf.getvalue()  #.................... Read traceback as a string
    tb_lines = tb_str.split("\n")  #.............. Split traceback into individual lines


#-- Re-initialize the e-paper driver locally in this function -------
    from drivers.screen_waveshare_2p7inch_module import EPD_2in7_V2

    try:
        epd = EPD_2in7_V2()
    except Exception as _e:
        print("EPD init failed inside show_exception_on_screen:", _e)
        print(tb_str)
        return


#-- Clear the landscape framebuffer and draw the header -------------
    epd.image1Gray_Landscape.fill(epd.white)

    epd.image1Gray_Landscape.text(
                        "ERROR",
                        5,
                        5,
                        epd.black
                    )

    epd.image1Gray_Landscape.text(
                        type(e).__name__,
                        5,
                        20,
                        epd.black
                    )


#-- Define layout parameters for the landscape screen ---------------
    x = 0
    y = 40
    line_height = 10
    max_y = 176 - line_height
    max_chars_per_line = 32


#-- Decide what content should be shown -----------------------------
    if show_traceback:
        # Show the full wrapped traceback
        display_lines = wrap_text(tb_str, max_chars_per_line)
    else:
        # Show only the final error message and the last traceback location
        error_message = str(e)
        if not error_message:
            error_message = type(e).__name__

        last_location = "Location: unknown"

        for line in tb_lines:
            stripped = line.strip()
            if stripped.startswith('File "') and ", line " in stripped:
                last_location = stripped

        summary_text = (
            "Message: " + error_message + "\n"
            + last_location
        )

        display_lines = wrap_text(summary_text, max_chars_per_line)


#-- Draw the prepared text lines into the landscape buffer ----------
    for line in display_lines:
        if y > max_y:
            break

        epd.image1Gray_Landscape.text(
                            line,
                            x,
                            y,
                            epd.black
                        )
        y += line_height


#-- Perform a full landscape refresh --------------------------------
    epd.display_Landscape(epd.buffer_1Gray_Landscape)

    return


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
