"""Main career dashboard: player stats, contract, and menu navigation."""

from __future__ import annotations

import curses

from nrl import config
from nrl.models import GameState, sort_ladder
from nrl.ui import screen as ui

MENU_ITEMS = [
    ("Play Next Match", "match"),
    ("Training Ground", "training"),
    ("Shop", "shop"),
    ("Relationships", "relationships"),
    ("League Ladder", "ladder"),
    ("Quit Career", "quit"),
]


def draw_dashboard(stdscr, state: GameState, selected: int) -> None:
    stdscr.erase()
    p = state.player
    team = state.my_team

    ui.center_text(stdscr, 0, "🏉 NRL CAREER SIMULATOR 🏉", ui.attr(ui.CP_TITLE, bold=True))
    ui.center_text(
        stdscr, 1,
        f"Season {state.season_no}  ·  Round {state.round_no}/{config.SEASON_ROUNDS}",
        ui.attr(ui.CP_DIM),
    )

    # Left panel: player stats
    ui.draw_box(stdscr, 3, 1, 13, 38, f"{p.name} · {team.abbrev}")
    row = 5
    for key in p.STAT_KEYS:
        ui.draw_meter(stdscr, row, 3, 15, getattr(p, key), key.capitalize())
        row += 1
    row += 1
    ui.draw_meter(stdscr, row, 3, 15, p.energy, "Energy")
    ui.safe_addstr(stdscr, row + 2, 3, f"Overall: {p.overall}", ui.attr(ui.CP_ACCENT, bold=True))
    ui.safe_addstr(stdscr, row + 2, 18, f"Cash: ${p.cash}", ui.attr(ui.CP_GOOD))

    # Right panel: contract + relationships
    ui.draw_box(stdscr, 3, 41, 13, 36, "Contract & Standing")
    if state.contract:
        ui.safe_addstr(stdscr, 5, 43, f"Club: {state.contract.club}")
        ui.safe_addstr(stdscr, 6, 43, f"Wage: ${state.contract.wage_per_match}/match")
        ui.safe_addstr(stdscr, 7, 43, f"Seasons left: {state.contract.seasons_left}")
    row = 9
    for key in p.REL_KEYS:
        ui.draw_meter(stdscr, row, 43, 12, getattr(p, key), key.capitalize())
        row += 1
    if p.is_benched:
        ui.safe_addstr(stdscr, row + 1, 43, "⚠ BENCHED - coach is furious!", ui.attr(ui.CP_BAD, bold=True))

    # Menu
    ui.draw_box(stdscr, 17, 1, len(MENU_ITEMS) + 2, 38, "Menu")
    for i, (label, _) in enumerate(MENU_ITEMS):
        marker = "▶ " if i == selected else "  "
        attrs = ui.attr(ui.CP_ACCENT, bold=True) | curses.A_REVERSE if i == selected else 0
        ui.safe_addstr(stdscr, 18 + i, 3, f"{marker}{label:<30}", attrs)

    max_y, _ = stdscr.getmaxyx()
    ui.safe_addstr(stdscr, max_y - 1, 1, "↑/↓ select · Enter confirm · q quit", ui.attr(ui.CP_DIM))
    stdscr.refresh()


def run_menu(stdscr, state: GameState) -> str:
    """Blocking menu loop. Returns the chosen action key."""
    selected = 0
    stdscr.nodelay(False)
    curses.curs_set(0)
    while True:
        draw_dashboard(stdscr, state, selected)
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            selected = (selected - 1) % len(MENU_ITEMS)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = (selected + 1) % len(MENU_ITEMS)
        elif key in (curses.KEY_ENTER, 10, 13):
            return MENU_ITEMS[selected][1]
        elif key == ord("q"):
            return "quit"


def show_ladder(stdscr, state: GameState) -> None:
    stdscr.erase()
    ui.center_text(stdscr, 0, "NRL LADDER", ui.attr(ui.CP_TITLE, bold=True))
    header = f"{'#':>2} {'Team':<28} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'PD':>5} {'Pts':>4}"
    ui.safe_addstr(stdscr, 2, 2, header, curses.A_BOLD)
    for pos, t in enumerate(sort_ladder(state.teams), start=1):
        mine = t.name == state.my_team.name
        attrs = ui.attr(ui.CP_GOOD, bold=True) if mine else 0
        line = (
            f"{pos:>2} {t.name:<28} {t.played:>3} {t.won:>3} {t.drawn:>3} "
            f"{t.lost:>3} {t.diff:>+5} {t.ladder_points:>4}"
        )
        ui.safe_addstr(stdscr, 2 + pos, 2, line, attrs)
    ui.safe_addstr(stdscr, 4 + len(state.teams), 2, "Press any key to return...", ui.attr(ui.CP_DIM))
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()
