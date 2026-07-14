"""The Playmaker Pass mini-game (vector shooting).

An ASCII field: you are '@' on the left, a defender 'X' lurks mid-field,
your winger 'O' streaks down the right edge. An arrow pivots up and down
in front of you - press [Space] to fire the pass along that vector.
Hit the winger's lane while missing the defender's reach to complete it.

Run standalone:  python3 -m nrl.minigames.pass_game
"""

from __future__ import annotations

import curses
import math
import random
from dataclasses import dataclass

from nrl.minigames.base import Oscillator, realtime_loop
from nrl.ui import screen as ui

FIELD_W = 60
FIELD_H = 16
MAX_ANGLE = 50.0  # degrees, up or down


@dataclass
class PassSetup:
    player_y: int
    player_x: int
    defender_y: int
    defender_x: int
    winger_y: int
    winger_x: int


def make_setup(rng: random.Random | None = None) -> PassSetup:
    rng = rng or random.Random()
    return PassSetup(
        player_y=FIELD_H // 2,
        player_x=3,
        defender_y=rng.randint(3, FIELD_H - 4),
        defender_x=FIELD_W // 2,
        winger_y=rng.randint(2, FIELD_H - 3),
        winger_x=FIELD_W - 5,
    )


def trajectory_y(setup: PassSetup, angle_deg: float, x: int) -> float:
    """Ball's row when it reaches column x (screen y grows downward)."""
    return setup.player_y - math.tan(math.radians(angle_deg)) * (x - setup.player_x)


def catch_radius(passing_stat: int) -> float:
    """Winger's catching reach in rows. Passing 0 -> 1.0, 100 -> 2.5."""
    return 1.0 + passing_stat * 0.015


DEFENDER_REACH = 1.4  # rows either side of the defender that intercept


@dataclass
class PassResult:
    intercepted: bool
    complete: bool

    @property
    def quality(self) -> str:
        if self.intercepted:
            return "intercepted"
        return "complete" if self.complete else "wasted"


def judge_pass(setup: PassSetup, angle_deg: float, passing_stat: int) -> PassResult:
    y_at_defender = trajectory_y(setup, angle_deg, setup.defender_x)
    if abs(y_at_defender - setup.defender_y) <= DEFENDER_REACH:
        return PassResult(intercepted=True, complete=False)
    y_at_winger = trajectory_y(setup, angle_deg, setup.winger_x)
    complete = abs(y_at_winger - setup.winger_y) <= catch_radius(passing_stat)
    return PassResult(intercepted=False, complete=complete)


def _draw_field(stdscr, setup: PassSetup, angle: float, winger_dir: int,
                ball_x: float | None = None) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    top = 2
    left = max(0, (max_x - FIELD_W) // 2)

    ui.center_text(stdscr, 0, "🏉 PLAYMAKER PASS - [SPACE] to release!", ui.attr(ui.CP_TITLE, bold=True))
    ui.draw_box(stdscr, top, left, FIELD_H + 2, FIELD_W + 2)

    def put(y: float, x: float, ch: str, attrs: int = 0) -> None:
        ui.safe_addstr(stdscr, top + 1 + round(y), left + 1 + round(x), ch, attrs)

    put(setup.player_y, setup.player_x, "@", ui.attr(ui.CP_GOOD, bold=True))
    put(setup.defender_y, setup.defender_x, "X", ui.attr(ui.CP_BAD, bold=True))
    arrow = "↑" if winger_dir < 0 else "↓"
    put(setup.winger_y, setup.winger_x, "O", ui.attr(ui.CP_ACCENT, bold=True))
    put(setup.winger_y, setup.winger_x + 1, arrow, ui.attr(ui.CP_DIM))

    # pivoting aim arrow: short segment showing the pass vector
    end_x = min(FIELD_W - 1, ball_x if ball_x is not None else setup.player_x + 8)
    step = 1
    for x in range(setup.player_x + 1, int(end_x), step):
        y = trajectory_y(setup, angle, x)
        if 0 <= y < FIELD_H:
            ch = "·" if ball_x is None else "○"
            put(y, x, ch, ui.attr(ui.CP_WARN, bold=ball_x is not None))


def play_pass(stdscr, passing_stat: int = 40, rng: random.Random | None = None) -> PassResult:
    rng = rng or random.Random()
    setup = make_setup(rng)
    angle_osc = Oscillator(-MAX_ANGLE, MAX_ANGLE, speed=95, start=0)
    winger_osc = Oscillator(2, FIELD_H - 3, speed=6, start=setup.winger_y)

    def update(dt, key):
        angle_osc.advance(dt)
        setup.winger_y = round(winger_osc.advance(dt))

    realtime_loop(
        stdscr,
        update=update,
        draw=lambda: _draw_field(stdscr, setup, angle_osc.value, winger_osc.direction),
    )
    angle = angle_osc.value
    result = judge_pass(setup, angle, passing_stat)

    # quick ball-flight animation along the locked vector
    for bx in range(setup.player_x + 2, FIELD_W - 2, 3):
        _draw_field(stdscr, setup, angle, winger_osc.direction, ball_x=bx)
        stdscr.refresh()
        curses.napms(40)
        if result.intercepted and bx >= setup.defender_x:
            break

    verdict = {
        "complete": ("✅ Cut-out ball! The winger takes it in stride!", ui.CP_GOOD),
        "intercepted": ("❌ INTERCEPTED! The defender reads it!", ui.CP_BAD),
        "wasted": ("😬 Sails into touch... wasted possession.", ui.CP_WARN),
    }[result.quality]
    ui.flash_message(stdscr, verdict[0], ui.attr(verdict[1], bold=True))
    return result


def main() -> None:
    def _run(stdscr):
        ui.init_colors()
        while True:
            result = play_pass(stdscr, passing_stat=40)
            stdscr.erase()
            ui.center_text(stdscr, 2, f"Result: {result.quality.upper()}")
            ui.center_text(stdscr, 4, "Press [r] to retry, any other key to quit")
            stdscr.nodelay(False)
            if stdscr.getch() != ord("r"):
                break

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
