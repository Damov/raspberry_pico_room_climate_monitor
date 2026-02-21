#!/usr/bin/env python3

"""
--------------------------------------------------------------------------
 SUMMARY:
--------------------------------------------------------------------------
 The updated script is a desktop Python tool  that converts a PNG  into a
 raw .bin file where each pixel is stored as one byte (0 or 255). It uses
 Pillow to open the image,  converts it to 1‑bit  black/white and then to
 8‑bit grayscale so each pixel becomes a single byte. The script flattens
 these pixels into a width * height byte  sequence and writes it to disk.
 In MicroPython you load this .bin into a bytearray and pass it, with the
 correct width and height, to add_image(), which expects exactly one byte
 per pixel.
--------------------------------------------------------------------------
"""
import argparse
from pathlib import Path
from PIL import Image


def png_to_8bpp_bytes(img: Image.Image) -> bytes:
    """
    Convert a PIL image to 8‑bit (1 byte per pixel) grayscale/mono.
    Each byte is a pixel value (0..255), suitable for code that
    treats img_buf[row_off + x] as a color.

    Arguments:
    ----------
        img: PIL.Image.Image
            The input image to convert. It can be in any mode (RGB, RGBA,
            etc.) but will be converted to 1‑bit black/white first.
    
    Returns:
    --------
        bytes
            A bytes object containing the pixel data in 8‑bit grayscale
            format, where each byte represents a pixel value (0 for black,
            255 for white).
    """
    # Convert to 1‑bit then to L mode so pixels are 0 or 255
    img = img.convert("1").convert("L")
    w, h = img.size
    # getdata() returns a flat sequence of length w*h
    return bytes(img.getdata())


def main():
    parser = argparse.ArgumentParser(
        description = "Convert a PNG to 8‑bit-per-pixel .bin for MicroPython framebuf/user code."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to input PNG image.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .bin path (default: same name with .bin).",
    )

    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    output_path = args.output
    if output_path is None:
        output_path = input_path.with_suffix(".bin")

    img = Image.open(input_path)
    data = png_to_8bpp_bytes(img)

    with open(output_path, "wb") as f:
        f.write(data)

    print(f"Saved {len(data)} bytes to {output_path}")
    print(f"Image size: {img.width}x{img.height}")
    print("In MicroPython, use len(buf) == width*height and pass buf to add_image().")

if __name__ == "__main__":
    main()
