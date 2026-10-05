"""Host-side regression tests for button timing and monitor integration."""

import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
TICKS_PERIOD = 1 << 30


class FakePin:
    IN = 0
    PULL_UP = 1

    def __init__(self, number=0, *args):
        self.number = number
        self.level = 1

    def value(self):
        return self.level


class FakeTimer:
    PERIODIC = 1

    def __init__(self, number):
        self.running = False

    def init(self, **kwargs):
        self.options = kwargs
        self.running = True

    def deinit(self):
        self.running = False


class ButtonTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.irq_disabled = False
        self.machine = SimpleNamespace(
            Timer=FakeTimer, Pin=FakePin,
            disable_irq=self.disable_irq, enable_irq=self.enable_irq,
        )
        utime = SimpleNamespace(ticks_ms=lambda: self.now, ticks_diff=self.ticks_diff)
        spec = importlib.util.spec_from_file_location(
            'test_button_controller', ROOT / 'src/button_controller.py'
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            'machine': self.machine, 'utime': utime,
            'micropython': SimpleNamespace(alloc_emergency_exception_buf=Mock()),
        }):
            spec.loader.exec_module(self.module)
        self.pins = tuple(FakePin(i) for i in range(4))
        self.buttons = self.module.ButtonController(self.pins)
        self.advance(50)

    def tearDown(self):
        self.buttons.close()
        self.assertFalse(self.irq_disabled)

    @staticmethod
    def ticks_diff(a, b):
        return (a - b + TICKS_PERIOD // 2) % TICKS_PERIOD - TICKS_PERIOD // 2

    def disable_irq(self):
        previous = self.irq_disabled
        self.irq_disabled = True
        return previous

    def enable_irq(self, previous):
        self.irq_disabled = previous

    def advance(self, duration):
        for _ in range(duration // 10):
            self.now = (self.now + 10) % TICKS_PERIOD
            if self.buttons._timer.running:
                self.buttons._timer.options['callback'](self.buttons._timer)

    def level(self, index, level, duration=50):
        self.pins[index].level = level
        self.advance(duration)

    def press(self, index):
        self.level(index, 0)
        self.level(index, 1)

    def drain(self):
        return [self.buttons.pop() for _ in range(self.buttons.pending())]

    def test_press_and_release_bounce(self):
        for level in (0, 1, 0, 1):
            self.level(2, level, 10)
        self.level(2, 0)
        self.assertEqual(self.drain(), [])
        for level in (1, 0, 1, 0):
            self.level(2, level, 10)
        self.level(2, 1)
        self.assertEqual(self.drain(), [3])
        self.press(2)
        self.assertEqual(self.drain(), [3])

    def test_long_hold_and_brief_release_do_not_repeat(self):
        self.level(2, 0, 5000)
        self.assertEqual(self.drain(), [])
        self.level(2, 1, 30)
        self.level(2, 0, 5000)
        self.assertEqual(self.drain(), [])
        self.level(2, 1)
        self.assertEqual(self.drain(), [3])
        self.advance(500)
        self.assertEqual(self.drain(), [])
        self.press(2)
        self.assertEqual(self.drain(), [3])

    def test_each_button_acts_only_after_stable_release(self):
        for index in range(4):
            with self.subTest(button=index + 1):
                self.level(index, 0, 1000)
                self.assertEqual(self.drain(), [])
                self.level(index, 1, 40)
                self.assertEqual(self.drain(), [])
                self.advance(10)
                self.assertEqual(self.drain(), [index + 1])
                self.advance(100)
                self.assertEqual(self.drain(), [])

    def test_clicks_follow_release_order(self):
        self.level(0, 0)
        self.level(2, 0)
        self.level(2, 1)
        self.level(0, 1)
        self.assertEqual(self.drain(), [3, 1])

    def test_short_glitch_does_not_trigger(self):
        self.level(2, 0, 30)
        self.level(2, 1)
        self.assertEqual(self.drain(), [])

    def test_startup_hold_is_ignored(self):
        self.buttons.close()
        self.pins[0].level = 0
        self.buttons = self.module.ButtonController(self.pins)
        self.advance(1000)
        self.assertEqual(self.drain(), [])
        self.level(0, 1)
        self.assertEqual(self.drain(), [])
        self.press(0)
        self.assertEqual(self.drain(), [1])

    def test_events_are_kept_without_main_loop_polling(self):
        for index in (2, 2, 1, 3, 0):
            self.press(index)
        self.assertEqual(self.drain(), [3, 3, 2, 4, 1])

    def test_simultaneous_buttons_are_independent_and_ordered(self):
        for pin in self.pins:
            pin.level = 0
        self.advance(500)
        self.assertEqual(self.drain(), [])
        for pin in self.pins:
            pin.level = 1
        self.advance(50)
        self.assertEqual(self.drain(), [1, 2, 3, 4])
        self.advance(500)
        self.assertEqual(self.drain(), [])

    def test_queue_wraparound_and_overflow(self):
        for _ in range(32):
            self.press(2)
        self.press(1)
        self.assertTrue(self.buttons.take_overflow())
        self.assertFalse(self.buttons.take_overflow())
        self.assertEqual(self.drain(), [3] * 32)
        self.press(1)
        self.assertEqual(self.drain(), [2])

    def test_debounce_across_tick_rollover(self):
        self.now = TICKS_PERIOD - 20
        self.press(2)
        self.assertEqual(self.drain(), [3])

    def test_mapping_and_layout_wraparound(self):
        apply = self.module.apply_button
        self.assertEqual(apply(3, 4), 0)
        self.assertEqual(apply(0, 3), 4)
        self.assertEqual(apply(4, 2), 0)
        self.assertEqual(apply(3, 1), 3)
        self.assertEqual(apply(apply(0, 2), 2), 2)

    def test_interactively_assigned_physical_buttons(self):
        # GP21 Refresh, GP20 Down, GP19 Up, GP18 Home.
        for index, expected_layout in enumerate((2, 3, 1, 0)):
            with self.subTest(pin=(21, 20, 19, 18)[index]):
                self.level(index, 0, 100)
                self.assertEqual(self.drain(), [])
                self.level(index, 1)
                events = self.drain()
                self.assertEqual(len(events), 1)
                self.assertEqual(self.module.apply_button(2, events[0]), expected_layout)

    def test_timer_configuration_and_cleanup(self):
        self.assertEqual(self.buttons._timer.options['period'], 10)
        self.assertTrue(self.buttons._timer.options['hard'])
        self.buttons.close()
        self.assertFalse(self.buttons._timer.running)

    def main_functions(self, namespace):
        tree = ast.parse((ROOT / 'src/main.py').read_text())
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        exec(compile(tree, 'main.py', 'exec'), namespace)
        return namespace

    def test_main_stops_timer_on_error_and_keyboard_interrupt(self):
        for error in (RuntimeError('sensor failure'), KeyboardInterrupt()):
            controller = Mock()
            namespace = self.main_functions({
                'machine': self.machine, 'ButtonController': Mock(return_value=controller),
            })
            namespace['_run_monitor'] = Mock(side_effect=error)
            with self.assertRaises(type(error)):
                namespace['main']()
            controller.close.assert_called_once()
            pins = namespace['ButtonController'].call_args.args[0]
            self.assertEqual(tuple(pin.number for pin in pins), (21, 20, 19, 18))

    def test_monitor_captures_busy_presses_without_extra_sensor_reads(self):
        layouts = []
        measurements = []
        samples = []
        writer = Mock()
        sensors = Mock()

        def read_co2():
            measurements.append(self.now)
            self.level(1, 0) #............................. Press Next during the sensor read
            self.level(1, 1)
            return 400, 22, 50

        def show():
            if layouts == [1]:
                self.press(1) #............................ Two separate Next presses during the first page refresh
                self.press(1)
            elif layouts == [1, 3]:
                self.level(0, 0, 500) #..................... Hold Refresh during the next update
            elif layouts == [1, 3, 3]:
                self.press(3) #............................ Home follows Refresh in the queue

        def sleep_ms(duration):
            if layouts == [1, 3] and self.pins[0].level == 0:
                self.assertEqual(self.buttons.pending(), 0)
                self.advance(500) #........................ Holding Refresh must not draw another page
                self.assertEqual(layouts, [1, 3])
                self.level(0, 1) #......................... Queue Refresh only after release stays stable
            if layouts == [1, 3, 3, 0]:
                raise KeyboardInterrupt()
            self.advance(duration)
            if self.now > 5000:
                self.fail('Monitor did not process queued actions')

        sensors.read_measurement.side_effect = read_co2
        sensors.read_compensated.return_value = (22, 1013, 50)
        writer.show.side_effect = lambda: show() if layouts else None
        manager = Mock()
        for number, name in enumerate((
            'screen1', 'screen2_24h_temperature_history',
            'screen3_24h_humidity_history', 'screen4_24h_co2_history',
            'screen5_24h_pressure_history',
        )):
            getattr(manager, name).side_effect = lambda *args, n=number: layouts.append(n)
        logger = Mock()
        logger.add.side_effect = lambda *args: samples.append(args)
        namespace = self.main_functions({
            'ticks_ms': lambda: self.now, 'ticks_diff': self.ticks_diff,
            'sleep_ms': sleep_ms, 'gc': Mock(), 'Logger': Mock(return_value=logger),
            'EPD_2in7_V2': Mock(), 'ScreenWriter': Mock(return_value=writer),
            'ScreenManager': Mock(return_value=manager),
            'BME280': Mock(return_value=sensors), 'SCD41': Mock(return_value=sensors),
            'OpenSansBold_28': None, 'OpenSansBold_20': None,
            'apply_button': self.module.apply_button,
        })
        namespace['print_mem'] = Mock()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            namespace['_run_monitor'](self.buttons)
        self.assertEqual(layouts, [1, 3, 3, 0])
        self.assertEqual(len(measurements), 1)
        self.assertEqual(len(samples), 8)
        self.assertEqual(writer.show.call_count, 6) #........ Two splash updates and four successfully drawn pages


if __name__ == '__main__':
    unittest.main()
