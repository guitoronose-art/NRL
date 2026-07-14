#!/usr/bin/env python3
"""NRL Career Simulator - entry point.

Usage:  python3 main.py
Standalone mini-game prototypes:
    python3 -m nrl.minigames.kick
    python3 -m nrl.minigames.pass_game
    python3 -m nrl.minigames.breakaway
    python3 -m nrl.minigames.training
"""

from __future__ import annotations

import curses
import random

from nrl import config, management, season
from nrl.match_engine import apply_post_match, play_match
from nrl.models import Contract, GameState, TeamRecord, sort_ladder
from nrl.ui import dashboard
from nrl.ui import screen as ui


def new_career() -> GameState:
    teams = [
        TeamRecord(name=n, abbrev=a, strength=random.randint(35, 75))
        for n, a in config.NRL_TEAMS
    ]
    state = GameState(teams=teams)
    state.player.team_idx = random.randrange(len(teams))
    state.contract = Contract(club=state.my_team.name, seasons_left=2)
    return state


def _show_lines(stdscr, title: str, lines: list[str]) -> None:
    stdscr.erase()
    ui.center_text(stdscr, 1, title, ui.attr(ui.CP_TITLE, bold=True))
    for i, line in enumerate(lines):
        ui.safe_addstr(stdscr, 3 + i, 4, line)
    max_y, _ = stdscr.getmaxyx()
    ui.safe_addstr(stdscr, max_y - 1, 2, "Press any key to continue...", ui.attr(ui.CP_DIM))
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


def play_round(stdscr, state: GameState, fixtures) -> None:
    p = state.player
    opp_idx = season.opponent_for(fixtures, state.round_no, p.team_idx)

    if opp_idx == season.BYE:
        state.my_team.record_bye()
        p.adjust("energy", +30)
        _show_lines(stdscr, f"ROUND {state.round_no} — BYE WEEK",
                    ["A week off. You rest up and recover 30% energy.",
                     f"{state.my_team.abbrev} banks {config.POINTS_BYE} competition points."])
    elif p.is_benched:
        opp = state.teams[opp_idx]
        rng = random.Random()
        mine = season.simulate_ai_score(state.my_team, opp, rng)
        theirs = season.simulate_ai_score(opp, state.my_team, rng)
        state.my_team.record_result(mine, theirs)
        opp.record_result(theirs, mine)
        p.adjust("coach", +8)  # doing your time wins him back
        p.adjust("energy", +10)
        _show_lines(stdscr, f"ROUND {state.round_no} — BENCHED",
                    ["The coach has dropped you. You watch from the sidelines.",
                     f"Final score: {state.my_team.abbrev} {mine} — {theirs} {opp.abbrev}",
                     "You trained hard all week. The coach noticed. (Coach +8)"])
    else:
        opp = state.teams[opp_idx]
        out = play_match(stdscr, state, opp)
        lines = apply_post_match(state, opp, out)
        header = "WIN" if out.my_score > out.opp_score else ("DRAW" if out.my_score == out.opp_score else "LOSS")
        _show_lines(stdscr, f"FULL TIME — {header} {out.my_score}-{out.opp_score}", lines)

    season.simulate_other_matches(state, fixtures)
    state.round_no += 1


def end_of_season(stdscr, state: GameState) -> bool:
    """Wrap the season, renew or terminate the contract. Returns False on career end."""
    p = state.player
    ladder = sort_ladder(state.teams)
    pos = next(i for i, t in enumerate(ladder, 1) if t.name == state.my_team.name)
    lines = [
        f"{state.my_team.name} finish the season in position {pos}.",
        f"Your season: {p.season_tries} tries, {p.season_goals} goals.",
    ]

    if state.contract:
        state.contract.seasons_left -= 1
        if state.contract.seasons_left <= 0:
            score = p.overall + p.coach // 2 + p.fans // 2
            if score >= 95:
                new_wage = int(state.contract.wage_per_match * 1.5)
                state.contract = Contract(club=state.my_team.name, wage_per_match=new_wage, seasons_left=2)
                lines.append(f"Contract renewed! New wage: ${new_wage}/match for 2 seasons.")
            else:
                lines.append("The club releases you. Your career is over.")
                _show_lines(stdscr, f"END OF SEASON {state.season_no}", lines)
                return False
        else:
            lines.append(f"{state.contract.seasons_left} season(s) left on your deal.")
    _show_lines(stdscr, f"END OF SEASON {state.season_no}", lines)

    # Reset for a new year
    state.season_no += 1
    state.round_no = 1
    p.career_year += 1
    p.season_tries = p.season_goals = 0
    p.energy = 100
    for t in state.teams:
        t.played = t.won = t.drawn = t.lost = 0
        t.points_for = t.points_against = t.ladder_points = 0
    return True


def career_loop(stdscr, state: GameState) -> None:
    fixtures = season.generate_fixtures(len(state.teams))
    while True:
        if state.round_no > config.SEASON_ROUNDS:
            if not end_of_season(stdscr, state):
                return
            continue
        action = dashboard.run_menu(stdscr, state)
        if action == "quit":
            return
        elif action == "ladder":
            dashboard.show_ladder(stdscr, state)
        elif action == "match":
            play_round(stdscr, state, fixtures)
        elif action == "training":
            management.training_screen(stdscr, state)
        elif action == "shop":
            management.shop_screen(stdscr, state)
        elif action == "relationships":
            management.relationships_screen(stdscr, state)


def main() -> None:
    def _run(stdscr):
        ui.init_colors()
        career_loop(stdscr, new_career())

    curses.wrapper(_run)


if __name__ == "__main__":
    main()
