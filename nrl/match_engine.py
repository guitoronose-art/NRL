"""The live match engine.

`plan_match` is pure logic: it lays out an 80-minute timeline of AI scores,
commentary beats, and interactive Player Moments. `play_match` is the curses
runner: a ticking scoreboard and commentary feed that pauses seamlessly into
the mini-games when a moment fires.
"""

from __future__ import annotations

import curses
import random
from dataclasses import dataclass, field

from nrl import config
from nrl.minigames.breakaway import play_breakaway
from nrl.minigames.kick import play_kick
from nrl.minigames.pass_game import play_pass
from nrl.models import GameState, TeamRecord, clamp
from nrl.ui import screen as ui

SURNAMES = [
    "Cleary", "Tedesco", "Munster", "Ponga", "Hughes", "Grant", "Cobbo",
    "Walsh", "Mitchell", "Crichton", "Yeo", "Fifita", "Tuilagi", "Katoa",
    "Brimson", "Haas", "Carrigan", "Moses", "Luai", "Hammer",
]

MOMENT_KINDS = ("breakaway", "pass", "bomb", "penalty_kick")

FLAVOUR = [
    "{p} kicks deep into the corner...",
    "{p} breaks the line down the short side!",
    "Big hit from {p} in midfield!",
    "{p} takes the high ball under pressure.",
    "Scrum feed to {t}, {p} at first receiver...",
    "{p} chances an offload... it sticks!",
    "Error! {t} cough it up in good field position.",
    "{p} makes 40 metres on the kick return!",
    "Penalty against {t} for holding down.",
    "{p} grubbers in behind... just too heavy.",
]


@dataclass
class MatchEvent:
    minute: int
    kind: str          # "commentary" | "ai_score" | "moment"
    text: str = ""
    side: int = 0      # 0 = my team, 1 = opposition (for ai_score)
    points: int = 0
    moment: str = ""   # one of MOMENT_KINDS


def effective(stat: int, energy: int) -> int:
    """Fatigue drains performance: 0 energy halves a stat."""
    return round(stat * (0.5 + 0.5 * energy / 100))


def pick_moments(player, rng: random.Random) -> list[str]:
    """Choose this match's Player Moments, shaped by relationships."""
    n = rng.randint(*config.MOMENTS_PER_MATCH)
    kinds = ["breakaway", "pass", "bomb", "penalty_kick"]
    weights = [3, 3, 2, 2]
    if player.teammates < config.COLD_SHOULDER_THRESHOLD:
        weights[1] = 1  # frozen out: far fewer passing moments
    return [rng.choices(kinds, weights)[0] for _ in range(n)]


def plan_match(state: GameState, opp: TeamRecord, rng: random.Random | None = None) -> list[MatchEvent]:
    rng = rng or random.Random()
    my, p = state.my_team, state.player
    events: list[MatchEvent] = []

    # Background AI scoring (your teammates score too, a touch less often
    # because the big plays are yours to make).
    for side, atk, dfn, damp in ((0, my, opp, 0.72), (1, opp, my, 1.0)):
        edge = (atk.strength - dfn.strength) / 100
        n_tries = max(0, round(rng.gauss((2.6 + 2.2 * edge) * damp, 1.0)))
        for _ in range(n_tries):
            converted = rng.random() < 0.72
            pts = 4 + (2 if converted else 0)
            name = rng.choice(SURNAMES)
            txt = f"TRY! {name} crosses for {atk.abbrev}!" + (" Conversion good." if converted else "")
            events.append(MatchEvent(rng.randint(2, 79), "ai_score", txt, side=side, points=pts))

    # Commentary beats every few minutes
    for m in range(3, config.MATCH_MINUTES, rng.randint(4, 7)):
        t = rng.choice((my, opp))
        events.append(MatchEvent(m, "commentary",
                                 rng.choice(FLAVOUR).format(p=rng.choice(SURNAMES), t=t.abbrev)))

    # Player Moments at spread-out minutes
    kinds = pick_moments(p, rng)
    minutes = sorted(rng.sample(range(8, 76), len(kinds)))
    for m, kind in zip(minutes, kinds):
        events.append(MatchEvent(m, "moment", moment=kind))

    events.sort(key=lambda e: (e.minute, e.kind != "commentary"))
    return events


MOMENT_INTROS = {
    "breakaway": "The defence splinters - YOU'RE THROUGH THE GAP!",
    "pass": "Overlap on! You're at first receiver with numbers out wide...",
    "bomb": "Last tackle. The coach wants the bomb - put it up!",
    "penalty_kick": "Penalty in front! You're taking the two.",
}


@dataclass
class MatchOutcome:
    my_score: int = 0
    opp_score: int = 0
    tries: int = 0
    goals: int = 0
    moments_won: int = 0
    moments_total: int = 0
    feed: list[str] = field(default_factory=list)


def _run_moment(stdscr, kind: str, state: GameState, out: MatchOutcome) -> None:
    p = state.player
    out.moments_total += 1
    stdscr.erase()
    ui.center_text(stdscr, 2, "⭐ PLAYER MOMENT ⭐", ui.attr(ui.CP_ACCENT, bold=True) | curses.A_BLINK)
    ui.center_text(stdscr, 4, MOMENT_INTROS[kind], ui.attr(ui.CP_WARN, bold=True))
    ui.center_text(stdscr, 6, "Get ready...", ui.attr(ui.CP_DIM))
    stdscr.refresh()
    curses.napms(1500)
    stdscr.erase()

    if kind == "breakaway":
        if play_breakaway(stdscr, effective(p.speed, p.energy)):
            out.my_score += 4
            out.tries += 1
            out.moments_won += 1
            p.season_tries += 1
            out.feed.append(f"TRY! {p.name} goes the length of the field!!")
            _conversion(stdscr, state, out)
        else:
            out.feed.append(f"{p.name} is dragged down just short!")
    elif kind == "pass":
        result = play_pass(stdscr, effective(p.passing, p.energy))
        if result.quality == "complete":
            out.my_score += 4
            out.moments_won += 1
            out.feed.append(f"TRY! {p.name}'s cut-out ball sends the winger over!")
            _conversion(stdscr, state, out)
        elif result.quality == "intercepted":
            out.opp_score += 4
            out.feed.append(f"Disaster! {p.name}'s pass is picked off and run back for a try!")
        else:
            out.feed.append(f"{p.name}'s pass floats into touch.")
    elif kind == "bomb":
        r = play_kick(stdscr, effective(p.kicking, p.energy), label="BOMB KICK - hang it high!")
        if r.success:
            out.my_score += 4
            out.moments_won += 1
            out.feed.append(f"{p.name}'s bomb is spilled - the winger pounces to score!")
            _conversion(stdscr, state, out)
        else:
            out.feed.append(f"{p.name}'s bomb sails dead. Seven-tackle set.")
    elif kind == "penalty_kick":
        r = play_kick(stdscr, effective(p.kicking, p.energy), label="PENALTY GOAL ATTEMPT")
        if r.success:
            out.my_score += 2
            out.goals += 1
            out.moments_won += 1
            p.season_goals += 1
            out.feed.append(f"{p.name} slots the penalty goal. Money.")
        else:
            out.feed.append(f"{p.name} pushes the penalty attempt wide.")

    p.adjust("energy", -6)


def _conversion(stdscr, state: GameState, out: MatchOutcome) -> None:
    p = state.player
    r = play_kick(stdscr, effective(p.kicking, p.energy), label="CONVERSION ATTEMPT")
    if r.success:
        out.my_score += 2
        out.goals += 1
        p.season_goals += 1
        out.feed.append(f"{p.name} adds the extras.")
    else:
        out.feed.append(f"{p.name} hooks the conversion.")


def _draw_scoreboard(stdscr, state: GameState, opp: TeamRecord, minute: int, out: MatchOutcome) -> None:
    stdscr.erase()
    my = state.my_team
    max_y, max_x = stdscr.getmaxyx()

    ui.draw_box(stdscr, 0, 1, 5, max_x - 2, f"Round {state.round_no}")
    score = f"{my.abbrev}  {out.my_score:>2}   —   {out.opp_score:<2}  {opp.abbrev}"
    ui.center_text(stdscr, 2, score, ui.attr(ui.CP_TITLE, bold=True))
    ui.center_text(stdscr, 3, f"⏱ {minute:02d}'", ui.attr(ui.CP_WARN, bold=True))

    ui.draw_box(stdscr, 6, 1, max_y - 8, max_x - 2, "Commentary")
    visible = out.feed[-(max_y - 11):]
    for i, line in enumerate(visible):
        hot = i == len(visible) - 1
        ui.safe_addstr(stdscr, 8 + i, 4, line,
                       ui.attr(ui.CP_GOOD, bold=True) if hot and "TRY" in line
                       else (curses.A_BOLD if hot else ui.attr(ui.CP_DIM)))
    ui.safe_addstr(stdscr, max_y - 1, 2, "live — Player Moments will interrupt automatically",
                   ui.attr(ui.CP_DIM))
    stdscr.refresh()


def play_match(stdscr, state: GameState, opp: TeamRecord,
               rng: random.Random | None = None) -> MatchOutcome:
    """Run the full interactive 80 minutes. Updates player, returns the outcome."""
    rng = rng or random.Random()
    events = plan_match(state, opp, rng)
    out = MatchOutcome()
    out.feed.append(f"Kick-off! {state.my_team.name} v {opp.name}.")

    stdscr.nodelay(True)
    curses.curs_set(0)
    idx = 0
    for minute in range(1, config.MATCH_MINUTES + 1):
        while idx < len(events) and events[idx].minute <= minute:
            ev = events[idx]
            idx += 1
            if ev.kind == "commentary":
                out.feed.append(ev.text)
            elif ev.kind == "ai_score":
                if ev.side == 0:
                    out.my_score += ev.points
                else:
                    out.opp_score += ev.points
                out.feed.append(ev.text)
            elif ev.kind == "moment":
                _draw_scoreboard(stdscr, state, opp, minute, out)
                curses.napms(400)
                _run_moment(stdscr, ev.moment, state, out)
                stdscr.nodelay(True)
        if minute == 40:
            out.feed.append(f"HALF TIME: {state.my_team.abbrev} {out.my_score} — {out.opp_score} {opp.abbrev}")
        _draw_scoreboard(stdscr, state, opp, minute, out)
        curses.napms(170)  # ~80 min in ~15s of real time between moments

    out.feed.append(f"FULL TIME: {state.my_team.abbrev} {out.my_score} — {out.opp_score} {opp.abbrev}")
    _draw_scoreboard(stdscr, state, opp, config.MATCH_MINUTES, out)
    curses.napms(600)
    return out


def apply_post_match(state: GameState, opp: TeamRecord, out: MatchOutcome) -> list[str]:
    """Ladder, wage, energy and relationship consequences. Returns summary lines."""
    p = state.player
    my = state.my_team
    my.record_result(out.my_score, out.opp_score)
    opp.record_result(out.opp_score, out.my_score)

    lines = []
    won = out.my_score > out.opp_score
    drew = out.my_score == out.opp_score
    if state.contract:
        p.cash += state.contract.wage_per_match
        lines.append(f"Match wage: +${state.contract.wage_per_match}")
    p.adjust("energy", -18)

    share = out.moments_won / out.moments_total if out.moments_total else 0.5
    if won:
        p.adjust("coach", +6)
        p.adjust("fans", +5)
        p.adjust("teammates", +4)
        lines.append("Victory! The sheds are buzzing.")
    elif drew:
        p.adjust("coach", +1)
        lines.append("A draw. Mixed feelings in the sheds.")
    else:
        p.adjust("coach", -5)
        p.adjust("fans", -3)
        lines.append("Loss. The coach glares at his clipboard.")
    if share >= 0.75:
        p.adjust("fans", +6)
        p.adjust("coach", +4)
        lines.append("You starred in the big moments - the crowd chants your name!")
    elif share <= 0.25:
        p.adjust("fans", -4)
        p.adjust("coach", -4)
        p.adjust("teammates", -2)
        lines.append("You fluffed the big moments... heads shake in the stands.")
    bonus = out.tries * 150 + out.goals * 40
    if bonus:
        p.cash += bonus
        lines.append(f"Performance bonuses: +${bonus}")
    return lines
