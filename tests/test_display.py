"""Verify repeated display transfers and switching from partial to full updates."""

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
        self.driver.init = lambda: self.operations.append(('reset', None))
        self.driver.send_command = lambda value: self.operations.append(('command', value))
        self.driver.send_data = lambda value: self.operations.append(('data', value))
        self.driver.TurnOnDisplay = lambda: self.operations.append(('refresh', 'full'))
        self.driver.TurnOnDisplay_Fast = lambda: self.operations.append(('refresh', 'fast'))
        self.driver.TurnOnDisplay_Partial = lambda: self.operations.append(('refresh', 'partial'))

    def check_transfer(self, image, mode):
        operations = list(self.operations)
        if mode == 'full':
            self.assertEqual(operations.pop(0), ('reset', None))
        expected_window = [
            ('command', 0x11), ('data', 3),
            ('command', 0x44), ('data', 0), ('data', 21),
            ('command', 0x45), ('data', 0), ('data', 0), ('data', 7), ('data', 1),
            ('command', 0x4E), ('data', 0),
            ('command', 0x4F), ('data', 0), ('data', 0), ('command', 0x24),
        ]
        self.assertEqual(operations[:len(expected_window)], expected_window)
        payload = operations[len(expected_window):-1]
        expected_pixels = [image[(21 - i) * 264 + j] for j in range(264) for i in range(22)]
        self.assertEqual(payload, [('data', pixel) for pixel in expected_pixels])
        self.assertEqual(operations[-1], ('refresh', mode))

    def test_repeated_full_frames_send_latest_pixels(self):
        for value in (0, 255, 85):
            self.operations.clear()
            image = bytes([value]) * 5808
            self.driver.display_Landscape(image)
            self.check_transfer(image, 'full')

    def test_full_after_partial_restores_controller_and_sends_new_frame(self):
        old_image = bytes([0]) * 5808
        self.driver.display_Landscape_Partial(old_image)
        self.check_transfer(old_image, 'partial')
        self.operations.clear()
        new_image = bytes(index % 256 for index in range(5808))
        self.driver.display_Landscape(new_image)
        self.check_transfer(new_image, 'full')

    def test_fast_then_full_restores_controller_and_addresses(self):
        image = bytes(index % 256 for index in range(5808))
        self.driver.display_Landscape_Fast(image)
        self.check_transfer(image, 'fast')
        self.operations.clear()
        self.driver.display_Landscape(image)
        self.check_transfer(image, 'full')


if __name__ == '__main__':
    unittest.main()
