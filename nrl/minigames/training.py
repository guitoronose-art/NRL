"""Training-ground timing mini-game.

A marker sweeps along a bar; a narrow target zone sits at a random spot.
Press [Space] inside the zone - the closer to dead centre, the bigger the
stat gain (0 to +3).
"""

from __future__ import annotations

import curses
import random

from nrl.minigames.base import Oscillator, realtime_loop
from nrl.ui import screen as ui

BAR_LO, BAR_HI = 0.0, 100.0
ZONE_HALF_WIDTH = 7.0


def judge_training(value: float, target: float) -> int:
    """Stat gain for locking at `value` against zone centre `target`."""
    miss = abs(value - target)
    if miss <= ZONE_HALF_WIDTH * 0.3:
        return 3
    if miss <= ZONE_HALF_WIDTH * 0.7:
        return 2
    if miss <= ZONE_HALF_WIDTH:
        return 1
    return 0


def play_training(stdscr, stat_name: str, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    target = rng.uniform(20, 80)
    osc = Oscillator(BAR_LO, BAR_HI, speed=120, start=0)

    def draw():
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        bar_w = min(60, max_x - 8)
        y, left = max_y // 2, (max_x - bar_w) // 2
        ui.center_text(stdscr, 1, f"🏋 TRAINING: {stat_name.upper()} - [SPACE] in the green!",
                       ui.attr(ui.CP_TITLE, bold=True))
        for i in range(bar_w):
            v = BAR_LO + (BAR_HI - BAR_LO) * i / (bar_w - 1)
            in_zone = abs(v - target) <= ZONE_HALF_WIDTH
            ch, attrs = ("▒", ui.attr(ui.CP_GOOD, bold=True)) if in_zone else ("─", ui.attr(ui.CP_DIM))
            ui.safe_addstr(stdscr, y, left + i, ch, attrs)
        col = left + round((osc.value - BAR_LO) / (BAR_HI - BAR_LO) * (bar_w - 1))
        ui.safe_addstr(stdscr, y - 1, col, "▼", ui.attr(ui.CP_WARN, bold=True))

    realtime_loop(stdscr, update=lambda dt, key: osc.advance(dt), draw=draw)
    gain = judge_training(osc.value, target)
    msg = {
        3: ("💪 PERFECT REP! Massive gains!", ui.CP_GOOD),
        2: ("Nice work. Solid session.", ui.CP_GOOD),
        1: ("Scrappy, but something stuck.", ui.CP_WARN),
        0: ("Sloppy session. No improvement.", ui.CP_BAD),
    }[gain]
    ui.flash_message(stdscr, msg[0], ui.attr(msg[1], bold=True))
    return gain


def main() -> None:
    def _run(stdscr):
        ui.init_colors()
        while True:
            gain = play_training(stdscr, "speed")
            stdscr.erase()
            ui.center_text(stdscr, 2, f"Gain: +{gain}")
            ui.center_text(stdscr, 4, "Press [r] to retry, any other key to quit")
            stdscr.nodelay(False)
            if stdscr.getch() != ord("r"):
                break

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
