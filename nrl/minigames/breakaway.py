"""The Breakaway Run mini-game (obstacle avoidance).

You've broken the line! For a few frantic seconds defenders ('X') rush in
from the right - steer '@' with [Up]/[Down] to dodge them. Survive the
sprint to plant it under the posts.

Run standalone:  python3 -m nrl.minigames.breakaway
"""

from __future__ import annotations

import curses
import random
from dataclasses import dataclass, field

from nrl.minigames.base import realtime_loop
from nrl.ui import screen as ui

FIELD_W = 62
FIELD_H = 12
RUN_SECONDS = 4.0
PLAYER_X = 4


@dataclass
class Defender:
    x: float
    y: int


@dataclass
class RunState:
    """Pure simulation state - advanced by tick(), no curses."""
    rng: random.Random
    speed_stat: int = 40
    player_y: int = FIELD_H // 2
    defenders: list[Defender] = field(default_factory=list)
    elapsed: float = 0.0
    spawn_timer: float = 0.0
    tackled: bool = False
    metres: float = 0.0

    @property
    def spawn_interval(self) -> float:
        """Faster players face slightly sparser traffic."""
        return 0.55 + self.speed_stat * 0.002

    def move(self, dy: int) -> None:
        self.player_y = max(0, min(FIELD_H - 1, self.player_y + dy))

    def tick(self, dt: float) -> None:
        if self.tackled:
            return
        self.elapsed += dt
        self.metres += dt * 22
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.defenders.append(Defender(x=FIELD_W - 1, y=self.rng.randrange(FIELD_H)))
        rush_speed = 26 + self.elapsed * 5  # they close in faster and faster
        for d in self.defenders:
            d.x -= rush_speed * dt
        self.defenders = [d for d in self.defenders if d.x > 0]
        if any(d.y == self.player_y and abs(d.x - PLAYER_X) < 1.2 for d in self.defenders):
            self.tackled = True

    @property
    def finished(self) -> bool:
        return self.tackled or self.elapsed >= RUN_SECONDS


def _draw(stdscr, run: RunState) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    top = 2
    left = max(0, (max_x - FIELD_W) // 2)

    remaining = max(0.0, RUN_SECONDS - run.elapsed)
    ui.center_text(stdscr, 0, "🏃 BREAKAWAY! Dodge with ↑/↓ !", ui.attr(ui.CP_TITLE, bold=True))
    ui.center_text(stdscr, 1, f"Try line in {remaining:0.1f}s · {run.metres:0.0f}m", ui.attr(ui.CP_WARN))
    ui.draw_box(stdscr, top, left, FIELD_H + 2, FIELD_W + 2)

    # streaking turf lines for a sense of speed
    for row in range(FIELD_H):
        phase = int(run.metres * 2 + row * 7) % 12
        for col in range(FIELD_W - phase - 1, 0, -12):
            ui.safe_addstr(stdscr, top + 1 + row, left + 1 + col, "-", ui.attr(ui.CP_DIM))

    ch = "@" if not run.tackled else "%"
    ui.safe_addstr(stdscr, top + 1 + run.player_y, left + 1 + PLAYER_X, ch,
                   ui.attr(ui.CP_BAD if run.tackled else ui.CP_GOOD, bold=True))
    for d in run.defenders:
        ui.safe_addstr(stdscr, top + 1 + d.y, left + 1 + round(d.x), "X", ui.attr(ui.CP_BAD, bold=True))


def play_breakaway(stdscr, speed_stat: int = 40, rng: random.Random | None = None) -> bool:
    """Returns True if the player scores the try."""
    run = RunState(rng=rng or random.Random(), speed_stat=speed_stat)

    def update(dt, key):
        if key in (curses.KEY_UP, ord("k")):
            run.move(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            run.move(+1)
        run.tick(dt)

    # No lock key: the loop ends when the run finishes. Use a key nobody
    # presses and rely on the timeout-style finish check inside update/draw.
    stdscr.nodelay(True)
    curses.curs_set(0)
    import time
    last = time.monotonic()
    while not run.finished:
        now = time.monotonic()
        dt, last = now - last, now
        key = stdscr.getch()
        update(dt, key if key != -1 else None)
        _draw(stdscr, run)
        stdscr.refresh()
        curses.napms(30)

    _draw(stdscr, run)
    if run.tackled:
        ui.flash_message(stdscr, "💥 WRAPPED UP! Bone-rattling tackle!", ui.attr(ui.CP_BAD, bold=True))
    else:
        ui.flash_message(stdscr, "🎉 TRY!!! Under the black dot!", ui.attr(ui.CP_GOOD, bold=True))
    return not run.tackled


def main() -> None:
    def _run(stdscr):
        ui.init_colors()
        while True:
            scored = play_breakaway(stdscr, speed_stat=40)
            stdscr.erase()
            ui.center_text(stdscr, 2, "TRY SCORED!" if scored else "Tackled short.")
            ui.center_text(stdscr, 4, "Press [r] to retry, any other key to quit")
            stdscr.nodelay(False)
            if stdscr.getch() != ord("r"):
                break

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
