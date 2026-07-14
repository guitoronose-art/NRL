"""The Goal Kick / Bomb Kick mini-game.

Phase 1: a vertical power bar oscillates fast - [Space] locks power.
Phase 2: a horizontal wind/angle bar oscillates - [Space] locks accuracy.
Success is judged by pure logic in `judge_kick`, tunable by the player's
Kicking stat (higher stat = wider sweet spots).

Run standalone to test real-time input:  python3 -m nrl.minigames.kick
"""

from __future__ import annotations

import curses
from dataclasses import dataclass

from nrl.minigames.base import Oscillator, realtime_loop
from nrl.ui import screen as ui

POWER_SWEET_CENTER = 75.0  # ideal power
ANGLE_SWEET_CENTER = 0.0   # dead centre; angle runs -50..+50


@dataclass
class KickResult:
    power: float
    angle: float
    power_ok: bool
    angle_ok: bool

    @property
    def success(self) -> bool:
        return self.power_ok and self.angle_ok

    @property
    def quality(self) -> str:
        if self.success and abs(self.power - POWER_SWEET_CENTER) < 4 and abs(self.angle) < 4:
            return "perfect"
        if self.success:
            return "good"
        return "miss"


def sweet_spot_width(kicking_stat: int) -> float:
    """Half-width of the success window. Kicking 0 -> 6, kicking 100 -> 16."""
    return 6.0 + kicking_stat * 0.10


def judge_kick(power: float, angle: float, kicking_stat: int) -> KickResult:
    w = sweet_spot_width(kicking_stat)
    return KickResult(
        power=power,
        angle=angle,
        power_ok=abs(power - POWER_SWEET_CENTER) <= w,
        angle_ok=abs(angle - ANGLE_SWEET_CENTER) <= w,
    )


def _draw_power_bar(stdscr, value: float, kicking_stat: int) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    bar_h = min(20, max_y - 8)
    top, cx = 3, max_x // 2

    ui.center_text(stdscr, 1, "⚡ POWER - press [SPACE] to lock!", ui.attr(ui.CP_TITLE, bold=True))

    w = sweet_spot_width(kicking_stat)
    for i in range(bar_h):
        # row 0 at top = 100 power
        level = 100 * (bar_h - 1 - i) / (bar_h - 1)
        in_sweet = abs(level - POWER_SWEET_CENTER) <= w
        fill_attr = ui.attr(ui.CP_GOOD, bold=True) if in_sweet else ui.attr(ui.CP_DIM)
        body = "▓▓▓▓" if level <= value else "    "
        ui.safe_addstr(stdscr, top + i, cx - 3, "│" + body + "│", fill_attr)
        if abs(level - value) < 100 / bar_h / 2:
            ui.safe_addstr(stdscr, top + i, cx + 4, f"◀ {value:3.0f}", ui.attr(ui.CP_WARN, bold=True))
    ui.safe_addstr(stdscr, top + bar_h, cx - 3, "└────┘")


def _draw_angle_bar(stdscr, value: float, power: float, kicking_stat: int) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    bar_w = min(50, max_x - 10)
    y, left = max_y // 2, (max_x - bar_w) // 2

    ui.center_text(stdscr, 1, "🌬 WIND / ANGLE - press [SPACE] at the centre!", ui.attr(ui.CP_TITLE, bold=True))
    ui.center_text(stdscr, 3, f"Power locked: {power:.0f}", ui.attr(ui.CP_DIM))

    w = sweet_spot_width(kicking_stat)
    for i in range(bar_w):
        # column maps to angle -50..+50
        ang = -50 + 100 * i / (bar_w - 1)
        in_sweet = abs(ang - ANGLE_SWEET_CENTER) <= w
        ch, attrs = ("▒", ui.attr(ui.CP_GOOD, bold=True)) if in_sweet else ("─", ui.attr(ui.CP_DIM))
        ui.safe_addstr(stdscr, y, left + i, ch, attrs)
    marker_col = left + round((value + 50) / 100 * (bar_w - 1))
    ui.safe_addstr(stdscr, y - 1, marker_col, "▼", ui.attr(ui.CP_WARN, bold=True))
    ui.safe_addstr(stdscr, y + 1, left, "◀ hook", ui.attr(ui.CP_DIM))
    ui.safe_addstr(stdscr, y + 1, left + bar_w - 7, "slice ▶", ui.attr(ui.CP_DIM))


def play_kick(stdscr, kicking_stat: int = 40, label: str = "CONVERSION ATTEMPT") -> KickResult:
    """Run the full two-phase kick. Returns a KickResult."""
    ui.center_text(stdscr, 0, label, ui.attr(ui.CP_ACCENT, bold=True))

    # Phase 1: power. Higher pressure = faster bar; stat doesn't slow it, it widens the target.
    power_osc = Oscillator(0, 100, speed=140)
    realtime_loop(
        stdscr,
        update=lambda dt, key: power_osc.advance(dt),
        draw=lambda: _draw_power_bar(stdscr, power_osc.value, kicking_stat),
    )
    power = power_osc.value

    # Phase 2: angle.
    angle_osc = Oscillator(-50, 50, speed=110, start=-50)
    realtime_loop(
        stdscr,
        update=lambda dt, key: angle_osc.advance(dt),
        draw=lambda: _draw_angle_bar(stdscr, angle_osc.value, power, kicking_stat),
    )

    result = judge_kick(power, angle_osc.value, kicking_stat)
    verdict = {
        "perfect": ("💯 PERFECT STRIKE! Right through the middle!", ui.CP_GOOD),
        "good": ("✅ It's good! The kick sails over!", ui.CP_GOOD),
        "miss": ("❌ Missed! It drifts wide...", ui.CP_BAD),
    }[result.quality]
    ui.flash_message(stdscr, verdict[0], ui.attr(verdict[1], bold=True))
    return result


def main() -> None:
    """Standalone prototype entry point."""
    def _run(stdscr):
        ui.init_colors()
        while True:
            result = play_kick(stdscr, kicking_stat=40)
            stdscr.erase()
            ui.center_text(stdscr, 2, f"power={result.power:.1f}  angle={result.angle:+.1f}  -> {result.quality.upper()}")
            ui.center_text(stdscr, 4, "Press [r] to retry, any other key to quit")
            stdscr.nodelay(False)
            if stdscr.getch() != ord("r"):
                break

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
