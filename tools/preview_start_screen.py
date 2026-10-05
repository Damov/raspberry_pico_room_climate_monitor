"""Render the actual start-screen layout and bundled fonts on a host (Pillow)."""
import ast
import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_layout():
    namespace = {'math': math}
    for name in ('OpenSansBold_12', 'OpenSansBold_20', 'OpenSansBold_28'):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'src/fonts' / (name + '.py'))
        font = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(font)
        namespace[name] = font
    tree = ast.parse((ROOT / 'src/screen_manager.py').read_text())
    tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    exec(compile(tree, 'screen_manager.py', 'exec'), namespace)
    return namespace


class PreviewWriter:
    """Host adapter that records text and checks every drawing boundary."""
    width, height = 264, 176

    def __init__(self, namespace, image=None):
        self.font = namespace['OpenSansBold_28']
        self.writer = self
        self.fb = self
        self.texts = []
        self.icons = []
        self.pixels = {}
        self.image = image
        if image is not None:
            from PIL import ImageDraw
            self.draw = ImageDraw.Draw(image)

    def change_font(self, font):
        self.font = font

    def stringlen(self, text):
        return sum(self.font.get_ch(char)[2] for char in text)

    def clear_fb(self, color=0xFF):
        self.texts.clear()
        self.icons.clear()
        self.pixels.clear()
        if self.image is not None:
            self.draw.rectangle((0, 0, 263, 175), fill=255 if color else 0)

    def line(self, x0, y0, x1, y1, color):
        for x, y in ((x0, y0), (x1, y1)):
            assert 0 <= x < self.width and 0 <= y < self.height, (x, y)
        if self.image is not None:
            self.draw.line((x0, y0, x1, y1), fill=255 if color else 0)

    def pixel(self, x, y, color):
        assert 0 <= x < self.width and 0 <= y < self.height, (x, y)
        self.pixels[x, y] = color
        if self.image is not None:
            self.image.putpixel((x, y), 255 if color else 0)

    def add_image(self, fname, img_w, img_h, x=0, y=0, do_gc=True,
                  show_after=True, invert_colors=True):
        assert not show_after, "Icons must not trigger their own refresh"
        assert 0 <= x and x + img_w <= self.width
        assert 0 <= y and y + img_h <= self.height
        data = (ROOT / 'src' / fname).read_bytes()
        assert len(data) == img_w * img_h, fname
        self.icons.append((fname, x, y, img_w, img_h))
        if self.image is not None:
            for row in range(img_h):
                for col in range(img_w):
                    value = data[row * img_w + col]
                    black = (value > 127) if invert_colors else (value <= 127)
                    self.image.putpixel((x + col, y + row), 0 if black else 255)

    def vline(self, x, y, length, color):
        self.line(x, y, x, y + length - 1, color)

    def add_text_horizontal_center(self, text, y, x_start=0, x_end=None, invert=True):
        x_end = self.width if x_end is None else x_end
        width = self.stringlen(text)
        assert width <= x_end - x_start, text
        x = x_start + (x_end - x_start - width) // 2
        self.add_text(text, x, y, invert)

    def add_text(self, text, x, y, invert=True):
        width, height = self.stringlen(text), self.font.height()
        assert 0 <= x and x + width <= self.width, (text, x, width)
        assert 0 <= y and y + height <= self.height, (text, y, height)
        self.texts.append((text, x, y, width, height))
        if self.image is None:
            return
        for char in text:
            data, height, width = self.font.get_ch(char)
            stride = (width + 7) // 8
            for row in range(height):
                for col in range(width):
                    bit = (data[row * stride + col // 8] >> (7 - col % 8)) & 1
                    self.image.putpixel((x + col, y + row), 0 if bit == invert else 255)
            x += width


def main():
    import argparse
    from PIL import Image
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='/tmp/climate-start-screen.png')
    parser.add_argument('--co2', type=float, default=1250)
    parser.add_argument('--pressure', type=float, default=1013.2)
    parser.add_argument('--altitude', type=float, default=50)
    args = parser.parse_args()
    namespace = load_layout()
    image = Image.new('L', (264, 176), 255)
    writer = PreviewWriter(namespace, image)
    manager = namespace['ScreenManager'](writer, altitude_m=args.altitude)
    manager.screen1(22.5, 45.0, args.pressure, args.co2, None, None, None)
    image.save(args.output)
    print(args.output)


if __name__ == '__main__':
    main()
