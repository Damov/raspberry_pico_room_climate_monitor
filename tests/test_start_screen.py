"""Check start-screen assessments, icons, and text placement."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('start_preview', ROOT / 'tools/preview_start_screen.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class StartScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = preview.load_layout()
        cls.manager_class = cls.namespace['ScreenManager']

    def setUp(self):
        self.writer = preview.PreviewWriter(self.namespace)
        self.manager = self.manager_class(self.writer, altitude_m=50)

    def test_co2_assessment_boundaries(self):
        for value, expected in ((400, 'Good'), (799, 'Good'), (800, 'Medium'),
                                (1199, 'Medium'), (1200, 'Bad'), (1999, 'Bad'),
                                (2000, 'Very Bad'), (99999, 'Very Bad')):
            with self.subTest(value=value):
                self.assertEqual(self.manager._co2_status(value), expected)

    def test_fill_clamps_but_actual_numeric_value_is_preserved(self):
        self.assertEqual(self.manager._co2_angle(0), self.manager._co2_angle(400))
        self.assertEqual(self.manager._co2_angle(99999), self.manager._co2_angle(2500))
        self.assertAlmostEqual(self.manager._co2_angle(400), 135 * math.pi / 180)
        self.assertAlmostEqual(self.manager._co2_angle(2500), 405 * math.pi / 180)
        self.manager.screen1(22.5, 45, 1013.2, 99999, None, None, None)
        self.assertIn('99999', [item[0] for item in self.writer.texts])
        self.assertIn('ppm', [item[0] for item in self.writer.texts])

    def test_fill_grows_and_clamps_at_both_endpoints(self):
        def black_pixels(co2):
            self.manager.screen1(22.5, 45, 1013.2, co2, None, None, None)
            return {point for point, color in self.writer.pixels.items() if color == 0}
        empty = black_pixels(400)
        self.assertEqual(black_pixels(0), empty)
        previous = empty
        for co2 in (800, 1200, 2000, 2500):
            current = black_pixels(co2)
            self.assertLess(previous, current)
            previous = current
        self.assertEqual(black_pixels(99999), previous)
        self.assertGreater(len(previous - empty), 1000)

    def test_fill_endpoint_and_empty_interior(self):
        self.manager.screen1(22.5, 45, 1013.2, 800, None, None, None)
        def point(degrees):
            angle = degrees * math.pi / 180
            return (67 + round(50 * math.cos(angle)), 82 + round(50 * math.sin(angle)))
        self.assertEqual(self.writer.pixels[point(160)], 0)
        self.assertEqual(self.writer.pixels[point(230)], 0xFF)
        self.assertNotIn((67, 82), self.writer.pixels)
        for x, y in self.writer.pixels:
            distance = (x - 67) ** 2 + (y - 82) ** 2
            self.assertGreaterEqual(distance, 46 ** 2)
            self.assertLess(distance, 54 ** 2)
        for text, x, y, width, height in self.writer.texts:
            self.assertFalse(any(x <= px < x + width and y <= py < y + height
                                 for px, py in self.writer.pixels), text)

    def test_rounded_track_and_fill_end_caps(self):
        def point(radius, angle):
            return (67 + round(radius * math.cos(angle)),
                    82 + round(radius * math.sin(angle)))
        self.manager.screen1(22.5, 45, 1013.2, 1600, None, None, None)
        start = self.manager._co2_angle(400)
        self.assertNotIn(point(53, start + 0.03), self.writer.pixels)
        self.assertEqual(self.writer.pixels[point(50, start + 0.105)], 0)
        end = self.manager._co2_angle(1600)
        self.assertEqual(self.writer.pixels[point(50, end + 0.06)], 0)
        self.assertEqual(self.writer.pixels[point(52, end + 0.075)], 0xFF)

    def test_altitude_correction_and_default_local_reference(self):
        local = self.manager_class(self.writer)
        self.assertEqual(local._sea_level_pressure(1013.2), 1013.2)
        self.assertAlmostEqual(self.manager._sea_level_pressure(1013.2), 1019.22696, places=3)
        higher = self.manager_class(self.writer, altitude_m=120)
        self.assertGreater(higher._sea_level_pressure(1013.2), self.manager._sea_level_pressure(1013.2))

    def test_pressure_status_boundaries(self):
        for value, expected in ((999.9, 'Low'), (1000, 'Normal'),
                                (1020, 'Normal'), (1020.1, 'High')):
            self.assertEqual(self.manager._pressure_status(value), expected)

    def test_pressure_value_and_status_are_shown_without_a_heading(self):
        self.manager.screen1(22.5, 45, 1015, 800, None, None, None)
        texts = [item[0] for item in self.writer.texts]
        self.assertFalse(any('Pressure' in text for text in texts))
        self.assertIn(f'{self.manager._sea_level_pressure(1015):.1f} hPa', texts)
        self.assertIn('High', texts)
        self.assertEqual(self.writer.font, self.namespace['OpenSansBold_28'])

    def test_larger_climate_icons_precede_values_in_separate_rows(self):
        self.manager.screen1(22.5, 45, 1013.2, 800, None, None, None)
        texts = [item[0] for item in self.writer.texts]
        self.assertNotIn('Temperature', texts)
        self.assertNotIn('Humidity', texts)
        self.assertIn('CO2', texts)
        self.assertNotIn('Pressure (sea)', texts)
        self.assertEqual([item[0] for item in self.writer.icons],
                         ['img/leaf.bin', 'img/thermometer.bin', 'img/water-drop.bin'])
        for name, x, y, width, height in self.writer.icons:
            data = (ROOT / 'src' / name).read_bytes()
            self.assertEqual(set(data), {0, 255})
            self.assertEqual(len(data), width * height)
            if name != 'img/leaf.bin':
                self.assertEqual(height, 32)
                value = next(item for item in self.writer.texts
                             if ('°C' if 'thermometer' in name else '%') in item[0])
                self.assertLess(x + width, value[1])
                self.assertEqual(y + height // 2, value[2] + value[4] // 2)

    def test_large_negative_value_uses_a_centered_fallback_font(self):
        self.manager.screen1(-100.0, 100.0, 1013.2, 800, None, None, None)
        for text, x, y, width, height in self.writer.texts:
            if '°C' in text:
                self.assertLessEqual(width, 92)
                self.assertLess(height, 28)
                self.assertEqual(y + height // 2, 28)

    def test_all_text_fits_and_does_not_overlap(self):
        for co2 in (400, 799, 800, 1200, 2000, 2500, 10000, 99999):
            with self.subTest(co2=co2):
                self.manager.screen1(99.9, 100.0, 1018.2, co2, None, None, None)
                rectangles = self.writer.texts + self.writer.icons
                for index, (text, x, y, width, height) in enumerate(rectangles):
                    for other, ox, oy, ow, oh in rectangles[index + 1:]:
                        overlap = x < ox + ow and ox < x + width and y < oy + oh and oy < y + height
                        self.assertFalse(overlap, (text, other))


if __name__ == '__main__':
    unittest.main()
