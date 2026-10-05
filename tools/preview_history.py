"""Render all four history pages with representative data (requires Pillow)."""
import argparse
import math
from PIL import Image
from preview_start_screen import load_layout, PreviewWriter


class PreviewHistory:
    """Representative oldest-first half-hour bins for previewing the layout."""
    def __init__(self, baseline, variation, empty=False):
        self.samples = [] if empty else [
            [86400 - index * 1800, baseline + variation * math.sin(index * math.pi / 12)]
            for index in range(49)]

    def count(self):
        return len(self.samples)

    def min(self):
        return min(value for age, value in self.samples)

    def max(self):
        return max(value for age, value in self.samples)

    def bin_series(self):
        return self.samples

    def max_bin_history_sec(self):
        return 86400


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='/tmp/climate-history-pages.png')
    parser.add_argument('--empty', action='store_true')
    args = parser.parse_args()
    namespace = load_layout()
    combined = Image.new('L', (264 * 4, 176), 255)
    pages = (
        ('screen2_24h_temperature_history', -5.0, 8.0, -2.5),
        ('screen3_24h_humidity_history', 45.0, 10.0, 45.0),
        ('screen4_24h_co2_history', 12000.0, 3000.0, 12345.0),
        ('screen5_24h_pressure_history', 1018.2, 3.0, 1018.2),
    )
    for index, (method, baseline, variation, current) in enumerate(pages):
        image = Image.new('L', (264, 176), 255)
        writer = PreviewWriter(namespace, image)
        manager = namespace['ScreenManager'](writer)
        getattr(manager, method)(current, PreviewHistory(baseline, variation, args.empty))
        combined.paste(image, (index * 264, 0))
    combined.save(args.output)
    print(args.output)


if __name__ == '__main__':
    main()
