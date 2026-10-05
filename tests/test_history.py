"""Verify live history bins, visible bars, and aligned history statistics."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('history_preview', ROOT / 'tools/preview_start_screen.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        clock = SimpleNamespace(
            ticks_ms=lambda: self.now,
            ticks_diff=lambda a, b: (a - b + (1 << 29)) % (1 << 30) - (1 << 29),
            ticks_add=lambda a, b: (a + b) % (1 << 30))
        tree = ast.parse((ROOT / 'src/logger.py').read_text())
        tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        namespace = {'time': clock}
        exec(compile(tree, 'logger.py', 'exec'), namespace)
        self.logger_class = namespace['Logger']
        self.logger = self.logger_class(86400, 1800)
        fonts = preview.load_layout()
        self.writer = preview.PreviewWriter(fonts)
        self.manager = fonts['ScreenManager'](self.writer)

    def add(self, seconds, value):
        self.now = int(seconds * 1000) % (1 << 30)
        self.logger.add(self.now, value)

    def plot(self, samples=None):
        self.writer.clear_fb()
        self.manager.draw_barplot(10, 30, 214, 85, 0, 0, 86400, 1200,
                                  self.logger.bin_series() if samples is None else samples)
        return self.writer.rectangles[:]

    def test_first_sample_and_active_bin_remain_visible(self):
        self.add(0, 400)
        first = self.plot()[0]
        self.assertEqual(first[2], 1)
        self.assertEqual(first[0] + first[2], 213)
        self.add(30, 600)
        self.assertEqual(self.logger.bin_series(), [[30, 500.0]])
        second = self.plot()[0]
        self.assertGreater(second[3], first[3])
        self.assertEqual(second[2], 1)
        self.assertFalse(any(x0 == x1 and color == 255
                             for x0, y0, x1, y1, color in self.writer.lines))

    def test_rollover_draws_oldest_and_current_bins_with_positive_widths(self):
        self.add(0, 400)
        self.add(30, 600)
        self.add(1800, 900)
        bars = self.plot()
        self.assertEqual(len(bars), 2)
        self.assertTrue(all(bar[2] > 0 and bar[3] > 0 for bar in bars))
        self.assertLessEqual(abs(bars[0][0] + bars[0][2] - bars[1][0]), 1)
        self.assertEqual(bars[-1][0] + bars[-1][2], 213)
        self.add(1830, 1000)
        self.assertEqual(self.logger.bin_series()[-1], [30, 950.0])
        self.assertGreater(self.plot()[-1][3], bars[-1][3])

    def test_all_bins_are_clipped_inside_the_plot_frame(self):
        bars = self.plot([[90000, 400], [88000, 600], [80000, 800], [0, 1000]])
        self.assertEqual(len(bars), 3)
        for x, y, width, height, color, fill in bars:
            self.assertGreaterEqual(x, 11)
            self.assertLessEqual(x + width, 213)
            self.assertGreaterEqual(y, 31)
            self.assertLessEqual(y + height, 84)

    def test_empty_history_draws_no_bars(self):
        self.assertEqual(self.plot(), [])

    def test_timestamp_wrap_preserves_active_bin_and_rollover(self):
        self.now = (1 << 30) - 10000
        self.logger.add(self.now, 400)
        self.now = 20000
        self.logger.add(self.now, 600)
        self.assertEqual(self.logger.bin_series(), [[30, 500.0]])
        self.assertGreater(self.plot()[0][2], 0)
        self.now = 1790000
        self.logger.add(self.now, 900)
        self.assertEqual(self.logger.count(), 2)
        self.assertTrue(all(bar[2] > 0 for bar in self.plot()))

    def test_statistics_fit_all_units_in_three_rows_with_one_value_column(self):
        for unit, current in (('°C', -100.0), ('%', 100.0), ('ppm', 99999.0), ('hPa', 1018.2)):
            with self.subTest(unit=unit):
                self.logger = self.logger_class(86400, 1800)
                self.add(0, current - 2)
                self.manager._screen2_template(current, self.logger, unit, '24h History')
                headings = [item for item in self.writer.texts if item[0] in ('Current', 'Min', 'Max')]
                values = [item for item in self.writer.texts if item[1] == 100]
                self.assertEqual([item[0] for item in headings], ['Current', 'Min', 'Max'])
                self.assertEqual([item[2] for item in headings], [108, 130, 152])
                self.assertTrue(all(item[1] == 10 for item in headings))
                self.assertEqual([x for text, x, y, width, height in values], [100, 100, 100])
                self.assertEqual([item[0] for item in values],
                                 [f'{current:.1f} {unit}', f'{current - 2:.1f} {unit}', f'{current:.1f} {unit}'])
                self.assertTrue(all(item[2] == y for item, y in zip(values, (108, 130, 152))))
                summary = [item for item in self.writer.texts if item[2] >= 108]
                for index, (text, x, y, width, height) in enumerate(summary):
                    for other, ox, oy, ow, oh in summary[index + 1:]:
                        self.assertFalse(x < ox + ow and ox < x + width and
                                         y < oy + oh and oy < y + height, (text, other))

    def test_empty_statistics_show_current_and_na_extrema(self):
        self.manager._screen2_template(1018.2, self.logger, 'hPa', '24h Pressure History')
        self.assertEqual([text for text, x, y, w, h in self.writer.texts if x == 100],
                         ['1018.2 hPa', 'n/a hPa', 'n/a hPa'])

    def test_statistics_use_a_common_smaller_font_for_large_values(self):
        self.manager._screen2_template(123456789012.0, self.logger, 'ppm', '24h CO2 History')
        values = [item for item in self.writer.texts if item[1] == 100]
        self.assertEqual(len({item[4] for item in values}), 1)
        self.assertLess(values[0][4], 20)
