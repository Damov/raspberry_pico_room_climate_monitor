"""Verify reference images, pixel orientation, and refresh-mode transitions."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class DisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'src/drivers/screen_waveshare_2p7inch_module.py'
        spec = importlib.util.spec_from_file_location('test_display_driver', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            'machine': SimpleNamespace(Pin=object, SPI=object),
            'framebuf': SimpleNamespace(), 'utime': SimpleNamespace(),
        }):
            spec.loader.exec_module(module)
        cls.driver_class = module.EPD_2in7_V2

    def setUp(self):
        self.driver = object.__new__(self.driver_class)
        self.driver.width = 176
        self.driver.height = 264
        self.operations = []
        self.driver.init = lambda: self.operations.append(('init', 'full'))
        self.driver.init_Fast = lambda: self.operations.append(('init', 'fast'))
        self.driver.reset = lambda: self.operations.append(('reset', None))
        self.driver.ReadBusy = lambda: self.operations.append(('wait', None))
        self.driver.send_command = lambda value: self.operations.append(('command', value))
        self.driver.send_data = lambda value: self.operations.append(('data', value))
        self.driver.TurnOnDisplay = lambda: self.operations.append(('refresh', 'full'))
        self.driver.TurnOnDisplay_Fast = lambda: self.operations.append(('refresh', 'fast'))
        self.driver.TurnOnDisplay_Partial = lambda: self.operations.append(('refresh', 'partial'))

    def transfer(self, image, plane):
        window = [
            ('command', 0x11), ('data', 3),
            ('command', 0x44), ('data', 0), ('data', 21),
            ('command', 0x45), ('data', 0), ('data', 0), ('data', 7), ('data', 1),
            ('command', 0x4E), ('data', 0),
            ('command', 0x4F), ('data', 0), ('data', 0), ('command', plane),
        ]
        pixels = [('data', image[(21 - i) * 264 + j]) for j in range(264) for i in range(22)]
        return window + pixels

    def check_transfer(self, image, mode):
        frame = self.transfer(image, 0x24)
        reference = self.transfer(image, 0x26)
        if mode == 'full':
            expected = [('init', 'full')] + frame + reference + [('refresh', 'full')]
        elif mode == 'fast':
            expected = [('init', 'fast')] + frame + [('refresh', 'fast')] + reference
        else:
            expected = [
                ('reset', None), ('wait', None), ('command', 0x3C), ('data', 0x80),
            ] + frame + [('refresh', 'partial')] + reference
        self.assertEqual(self.operations, expected)

    def test_repeated_full_frames_seed_both_planes(self):
        for value in (0, 255, 85):
            self.operations.clear()
            image = bytes([value]) * 5808
            self.driver.display_Landscape(image)
            self.check_transfer(image, 'full')

    def test_full_then_multiple_partials_preserve_the_latest_reference(self):
        for mode, value in [('full', 0), ('partial', 255), ('partial', 85), ('full', 170)]:
            self.operations.clear()
            image = bytes([value]) * 5808
            getattr(self.driver, 'display_Landscape' + ('_Partial' if mode == 'partial' else ''))(image)
            self.check_transfer(image, mode)

    def test_fast_then_partial_then_full_preserves_pixel_orientation(self):
        image = bytes(index % 256 for index in range(5808))
        for mode, method in [('fast', 'Fast'), ('partial', 'Partial'), ('full', '')]:
            self.operations.clear()
            getattr(self.driver, 'display_Landscape' + ('_' + method if method else ''))(image)
            self.check_transfer(image, mode)

    def test_failed_partial_does_not_replace_the_reference_image(self):
        def fail_refresh():
            raise OSError('display failure')
        self.driver.TurnOnDisplay_Partial = fail_refresh
        with self.assertRaises(OSError):
            self.driver.display_Landscape_Partial(bytes([0]) * 5808)
        self.assertNotIn(('command', 0x26), self.operations)


if __name__ == '__main__':
    unittest.main()
