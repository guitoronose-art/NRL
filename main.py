#!/usr/bin/env python3
"""NRL Career Simulator - entry point.

Usage:  python3 main.py
Standalone kick prototype:  python3 -m nrl.minigames.kick
"""

from __future__ import annotations

import curses
import random

from nrl import config
from nrl.minigames.kick import play_kick
from nrl.models import Contract, GameState, TeamRecord
from nrl.ui import dashboard
from nrl.ui import screen as ui


def new_career() -> GameState:
    teams = [
        TeamRecord(name=n, abbrev=a, strength=random.randint(35, 75))
        for n, a in config.NRL_TEAMS
    ]
    state = GameState(teams=teams)
    state.player.team_idx = random.randrange(len(teams))
    state.contract = Contract(club=state.my_team.name)
    return state


def career_loop(stdscr, state: GameState) -> None:
    while True:
        action = dashboard.run_menu(stdscr, state)
        if action == "quit":
            return
        elif action == "ladder":
            dashboard.show_ladder(stdscr, state)
        elif action == "match":
            # Full match engine lands in step 3; for now, exercise the kick
            # mini-game as a taste of a Player Moment.
            stdscr.erase()
            result = play_kick(stdscr, kicking_stat=state.player.kicking)
            if result.success:
                state.player.season_goals += 1
                state.player.adjust("fans", +2)
            else:
                state.player.adjust("fans", -1)
        else:
            stdscr.erase()
            ui.flash_message(stdscr, f"'{action}' coming in a later step!", ui.attr(ui.CP_WARN))


def main() -> None:
    def _run(stdscr):
        ui.init_colors()
        career_loop(stdscr, new_career())

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
