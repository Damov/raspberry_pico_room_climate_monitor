"""Verify cleaning intervals, manual refreshes, and successful state updates."""

import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'src/main.py').read_text())
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'refresh_screen']
        namespace = {
            'ticks_ms': lambda: self.now,
            'ticks_diff': lambda a, b: (a - b + (1 << 29)) % (1 << 30) - (1 << 29),
            'print': lambda *args: None,
        }
        exec(compile(tree, 'main.py', 'exec'), namespace)
        self.refresh = namespace['refresh_screen']
        self.writer = Mock()
        self.state = {'last_full': 0, 'last_partial': 0, 'soft_updates': 0}

    def test_five_soft_updates_then_one_cleaning_full_refresh(self):
        for cycle in range(1, 13):
            self.now += 30000
            result = self.refresh(self.writer, self.state, measurement_due=True)
            self.assertEqual(result, 'full' if cycle % 6 == 0 else 'partial')
            self.assertEqual(self.state['soft_updates'], cycle % 6)
        self.assertEqual(self.writer.show_partial.call_count, 10)
        self.assertEqual(self.writer.show.call_count, 2)
        self.writer.show_fast.assert_not_called()

    def test_manual_full_refresh_restarts_timers_and_cleaning_count(self):
        self.state['soft_updates'] = 4
        self.now = 60000
        self.assertEqual(self.refresh(self.writer, self.state, force_full=True, measurement_due=True), 'full')
        self.assertEqual(self.state, {'last_full': 60000, 'last_partial': 60000, 'soft_updates': 0})
        self.writer.show_partial.assert_not_called()
        self.assertIsNone(self.refresh(self.writer, self.state))
        self.now += 30000
        self.assertEqual(self.refresh(self.writer, self.state, measurement_due=True), 'partial')

    def test_elapsed_full_interval_takes_priority_over_new_measurement(self):
        self.now = 15 * 60 * 1000
        self.assertEqual(self.refresh(self.writer, self.state, measurement_due=True), 'full')
        self.writer.show.assert_called_once()
        self.writer.show_partial.assert_not_called()

    def test_failed_full_and_partial_leave_scheduling_state_unchanged(self):
        for force_full in (True, False):
            with self.subTest(force_full=force_full):
                self.now = 30000
                original = dict(self.state)
                writer = Mock()
                getattr(writer, 'show' if force_full else 'show_partial').side_effect = OSError('failed refresh')
                with self.assertRaises(OSError):
                    self.refresh(writer, self.state, force_full=force_full, measurement_due=True)
                self.assertEqual(self.state, original)

    def test_timestamps_are_recorded_after_transfer_completion(self):
        def complete():
            self.now += 2500
        self.writer.show.side_effect = complete
        self.refresh(self.writer, self.state, force_full=True)
        self.assertEqual(self.state['last_full'], 2500)
        self.assertEqual(self.state['last_partial'], 2500)
        self.now = 30000
        self.writer.show_partial.side_effect = complete
        self.refresh(self.writer, self.state, measurement_due=True)
        self.assertEqual(self.state['last_partial'], 32500)
        self.assertEqual(self.state['soft_updates'], 1)

    def test_full_interval_across_tick_rollover(self):
        self.state['last_full'] = (1 << 30) - 1000
        self.now = 15 * 60 * 1000 - 1000
        self.assertEqual(self.refresh(self.writer, self.state, measurement_due=True), 'full')


if __name__ == '__main__':
    unittest.main()
