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
        self.gpio = []
        self.spi_rows = []
        self.row_ids = []
        self.driver._landscape_row = bytearray(22)
        self.driver.dc_pin = 'dc'
        self.driver.cs_pin = 'cs'
        self.driver.reset_pin = 'reset'
        self.driver.digital_write = lambda pin, value: self.gpio.append((pin, value))

        def write_row(row):
            self.spi_rows.append(bytes(row))
            self.row_ids.append(id(row))
            self.operations.extend(('data', value) for value in row)
        self.driver.spi = SimpleNamespace(write=write_row)
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

    def test_spi_batches_reuse_one_row_and_release_chip_select(self):
        image = bytes(index % 256 for index in range(5808))
        self.driver.display_Landscape(image)
        self.assertEqual(len(self.spi_rows), 528)
        self.assertTrue(all(len(row) == 22 for row in self.spi_rows))
        self.assertEqual(set(self.row_ids), {id(self.driver._landscape_row)})
        self.assertEqual(self.gpio, [('dc', 1), ('cs', 0), ('cs', 1)] * 2)
        self.check_transfer(image, 'full')

    def test_spi_failure_releases_chip_select_and_does_not_activate_display(self):
        def fail_write(row):
            raise OSError('SPI write failed')
        self.driver.spi.write = fail_write
        with self.assertRaises(OSError):
            self.driver.display_Landscape(bytes([0]) * 5808)
        self.assertEqual(self.gpio[-1], ('cs', 1))
        self.assertNotIn(('refresh', 'full'), self.operations)
        self.assertNotIn(('command', 0x26), self.operations)

    def test_reset_uses_reference_timing(self):
        delays = []
        self.driver.delay_ms = delays.append
        self.driver_class.reset(self.driver)
        self.assertEqual(delays, [20, 2, 20])
        self.assertEqual(self.gpio, [('reset', 1), ('reset', 0), ('reset', 1)])

    def test_busy_wait_polls_until_ready_then_settles_for_20_ms(self):
        readings = iter([1, 1, 0])
        self.driver.busy_pin = 'busy'
        self.driver.digital_read = lambda pin: next(readings)
        delays = []
        self.driver.delay_ms = delays.append
        self.driver_class.ReadBusy(self.driver)
        self.assertEqual(delays, [2, 2, 20])

    def test_failed_partial_does_not_replace_the_reference_image(self):
        def fail_refresh():
            raise OSError('display failure')
        self.driver.TurnOnDisplay_Partial = fail_refresh
        with self.assertRaises(OSError):
            self.driver.display_Landscape_Partial(bytes([0]) * 5808)
        self.assertNotIn(('command', 0x26), self.operations)


if __name__ == '__main__':
    unittest.main()
