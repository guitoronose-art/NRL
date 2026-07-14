"""Shared real-time loop utilities for mini-games.

Mini-games run a fixed-timestep loop: poll input with nodelay getch,
advance simulation, redraw, then sleep the remainder of the frame.
"""

from __future__ import annotations

import curses
import time

FRAME_MS = 33  # ~30 fps


class Oscillator:
    """A value bouncing between lo and hi at a given speed (units/second).

    Pure logic - no curses - so trajectories are unit-testable.
    """

    def __init__(self, lo: float, hi: float, speed: float, start: float | None = None):
        self.lo = lo
        self.hi = hi
        self.speed = speed
        self.value = lo if start is None else start
        self.direction = 1

    def advance(self, dt: float) -> float:
        self.value += self.direction * self.speed * dt
        # bounce, handling overshoot so fast speeds stay in range
        while self.value > self.hi or self.value < self.lo:
            if self.value > self.hi:
                self.value = 2 * self.hi - self.value
                self.direction = -1
            elif self.value < self.lo:
                self.value = 2 * self.lo - self.value
                self.direction = 1
        return self.value


def realtime_loop(stdscr, update, draw, lock_keys=(ord(" "),), timeout_s: float | None = None):
    """Run update(dt)/draw() every frame until a lock key is pressed.

    Returns the key pressed, or None on timeout. Arrow keys etc. are passed
    to update via update(dt, key).
    """
    stdscr.nodelay(True)
    curses.curs_set(0)
    start = last = time.monotonic()
    while True:
        now = time.monotonic()
        dt, last = now - last, now
        if timeout_s is not None and now - start >= timeout_s:
            return None
        key = stdscr.getch()
        if key in lock_keys:
            return key
        update(dt, key if key != -1 else None)
        draw()
        stdscr.refresh()
        elapsed_ms = (time.monotonic() - now) * 1000
        curses.napms(max(1, int(FRAME_MS - elapsed_ms)))
