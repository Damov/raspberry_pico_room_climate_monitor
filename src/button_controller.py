"""
=============================================================================
button_controller.py

Debounced button input for the Raspberry Pico Room Climate Monitor. A hard
interrupt timer captures presses while sensors and the display are busy.

Part of the Open source project: Raspberry Pico Room Climate Monitor
See: https://github.com/Damov/raspberry_pico_room_climate_monitor
=============================================================================
"""

import machine
import micropython
from utime import ticks_ms, ticks_diff


class ButtonController:
    """
        Sample active-low buttons and queue one event per completed press and release.

        Arguments:
        ----------
            pins: tuple
                K1, K2, K3, K4 input pins, in that order.

        Notes:
        ------
            Requires MicroPython 1.27 or newer on RP2. Press and release must
            remain stable for 40 ms. Holding a button does nothing; the action
            triggers on release. Buttons held at startup are ignored until
            released, without triggering an action on that initial release. The main
            loop handles navigation and display updates.
    """
    SAMPLE_INTERVAL_MS = 10
    DEBOUNCE_MS = 40
    QUEUE_SIZE = 32

    def __init__(self, pins):
    #-- Allocate all state before starting the interrupt timer ------------
        self._pins = pins
        self._raw = bytearray(pin.value() for pin in pins)
        self._stable = bytearray(self._raw)
        self._armed = bytearray(len(pins)) #............... Require a stable release before the first press
        self._pressed = bytearray(len(pins)) #............. Remember valid presses until their stable release
        self._changed_at = [ticks_ms()] * len(pins)
        self._queue = bytearray(self.QUEUE_SIZE)
        self._head = 0
        self._tail = 0
        self._count = 0
        self._overflow = False
        self._timer = machine.Timer(-1)
        micropython.alloc_emergency_exception_buf(100) #... Allow interrupt errors to include a traceback

    #-- Start sampling independently of the main loop ---------------------
        try:
            self._timer.init(
                period=self.SAMPLE_INTERVAL_MS,
                mode=machine.Timer.PERIODIC,
                callback=self._sample,
                hard=True
            )
        except BaseException:
            self._timer.deinit()
            raise

    def _sample(self, timer):
        """
            Debounce input and enqueue completed clicks in K1-K4 release order.

            This runs in hard interrupt context: do not allocate memory, print,
            sleep, access sensors, or update the display here. Queue indices and
            counters stay bounded so their arithmetic uses small integers.
        """
        now = ticks_ms()
        index = 0
        while index < len(self._pins):
            value = self._pins[index].value()
            if value != self._raw[index]:
                self._raw[index] = value
                self._changed_at[index] = now
            elif ticks_diff(now, self._changed_at[index]) >= self.DEBOUNCE_MS:
                if value == 1:
                    self._stable[index] = 1
                    if self._pressed[index]:
                        self._pressed[index] = 0 #........ Consume the click exactly once after stable release
                        if self._count < self.QUEUE_SIZE:
                            self._queue[self._tail] = index + 1
                            self._tail = (self._tail + 1) % self.QUEUE_SIZE
                            self._count += 1
                        else:
                            self._overflow = True #....... Keep older events and discard this completed click
                    self._armed[index] = 1 #............... Allow a new press after the stable release
                elif self._stable[index] != 0:
                    self._stable[index] = 0
                    if self._armed[index]:
                        self._armed[index] = 0
                        self._pressed[index] = 1 #........ Remember the press; holding never queues an action
            index += 1

    def pending(self):
        """Return the current number of queued clicks for one bounded batch."""
        return self._count

    def pop(self):
        """Return the oldest completed click as a button number (1-4), or zero if the queue is empty."""
    #-- Protect shared queue state from the sampling interrupt ------------
        irq_state = machine.disable_irq()
        try:
            if not self._count:
                return 0
            button = self._queue[self._head]
            self._head = (self._head + 1) % self.QUEUE_SIZE
            self._count -= 1
            return button
        finally:
            machine.enable_irq(irq_state)

    def take_overflow(self):
        """Read and clear the overflow flag; report it only from the main loop."""
        irq_state = machine.disable_irq()
        try:
            overflow = self._overflow
            self._overflow = False
            return overflow
        finally:
            machine.enable_irq(irq_state)

    def close(self):
        """Stop sampling before returning to the REPL or handling an error."""
        self._timer.deinit()


def apply_button(layout, button, layout_count=5):
    """Return the selected layout using K1 Refresh, K2 Next, K3 Previous, K4 Home."""
    if button == 4:
        return 0
    if button == 3:
        return (layout - 1) % layout_count
    if button == 2:
        return (layout + 1) % layout_count
    return layout #........................................ K1 requests a refresh without changing the page
