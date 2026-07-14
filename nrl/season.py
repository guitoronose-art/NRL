"""Season fixtures and AI match simulation. Pure logic - no curses."""

from __future__ import annotations

import random

from nrl import config
from nrl.models import GameState, TeamRecord

BYE = -1  # sentinel opponent index for the bye week


def generate_fixtures(num_teams: int, rounds: int = config.SEASON_ROUNDS) -> list[list[tuple[int, int]]]:
    """Round-robin fixtures via the circle method.

    With an odd team count a dummy slot gives one team a bye each round;
    that pairing is emitted as (team, BYE). Returns rounds as lists of
    (home, away) index pairs. If `rounds` exceeds a single round-robin,
    the cycle repeats with venues flipped.
    """
    ids = list(range(num_teams))
    if num_teams % 2 == 1:
        ids.append(BYE)
    n = len(ids)
    base_rounds: list[list[tuple[int, int]]] = []
    order = ids[:]
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = order[i], order[n - 1 - i]
            pairs.append((a, b))
        base_rounds.append(pairs)
        # rotate all but the first element
        order = [order[0]] + [order[-1]] + order[1:-1]

    fixtures = []
    for r in range(rounds):
        pairs = base_rounds[r % len(base_rounds)]
        if (r // len(base_rounds)) % 2 == 1:  # flip venues on the repeat cycle
            pairs = [(b, a) for a, b in pairs]
        # normalise so the bye sentinel is always second in the pair
        fixtures.append([(b, a) if a == BYE else (a, b) for a, b in pairs])
    return fixtures


def opponent_for(fixtures: list[list[tuple[int, int]]], round_no: int, team_idx: int) -> int | None:
    """Return opponent index for team in a 1-based round, BYE for a bye, None if not found."""
    for a, b in fixtures[round_no - 1]:
        if a == team_idx:
            return b
        if b == team_idx:
            return a
    return None


def simulate_ai_score(attack: TeamRecord, defence: TeamRecord, rng: random.Random) -> int:
    """A plausible NRL score for one side based on relative strength."""
    edge = (attack.strength - defence.strength) / 100
    tries = max(0, round(rng.gauss(3 + 2.5 * edge, 1.3)))
    conversions = sum(1 for _ in range(tries) if rng.random() < 0.72)
    penalty_goals = rng.choice([0, 0, 0, 1, 1, 2])
    return tries * 4 + conversions * 2 + penalty_goals * 2


def simulate_other_matches(state: GameState, fixtures, rng: random.Random | None = None) -> list[str]:
    """Simulate every match this round except the player's. Returns result lines."""
    rng = rng or random.Random()
    results = []
    me = state.player.team_idx
    for a, b in fixtures[state.round_no - 1]:
        if me in (a, b):
            continue
        if b == BYE:
            state.teams[a].record_bye()
            results.append(f"{state.teams[a].abbrev}  — bye —")
            continue
        ta, tb = state.teams[a], state.teams[b]
        sa, sb = simulate_ai_score(ta, tb, rng), simulate_ai_score(tb, ta, rng)
        ta.record_result(sa, sb)
        tb.record_result(sb, sa)
        results.append(f"{ta.abbrev} {sa:>2} — {sb:<2} {tb.abbrev}")
    return results
