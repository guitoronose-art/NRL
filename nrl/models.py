"""Core data models. Pure Python, no curses - fully unit-testable."""

from __future__ import annotations

from dataclasses import dataclass, field

from nrl import config


def clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


@dataclass
class Player:
    name: str = "Rookie"
    team_idx: int = 0
    speed: int = config.STARTING_STATS["speed"]
    strength: int = config.STARTING_STATS["strength"]
    passing: int = config.STARTING_STATS["passing"]
    kicking: int = config.STARTING_STATS["kicking"]
    tackle: int = config.STARTING_STATS["tackle"]
    energy: int = config.STARTING_ENERGY
    cash: int = config.STARTING_CASH
    coach: int = config.STARTING_RELATIONSHIPS["coach"]
    teammates: int = config.STARTING_RELATIONSHIPS["teammates"]
    fans: int = config.STARTING_RELATIONSHIPS["fans"]
    season_tries: int = 0
    season_goals: int = 0
    career_year: int = 1

    STAT_KEYS = ("speed", "strength", "passing", "kicking", "tackle")
    REL_KEYS = ("coach", "teammates", "fans")

    def adjust(self, key: str, delta: int) -> None:
        setattr(self, key, int(clamp(getattr(self, key) + delta)))

    @property
    def overall(self) -> int:
        return round(sum(getattr(self, k) for k in self.STAT_KEYS) / len(self.STAT_KEYS))

    @property
    def is_benched(self) -> bool:
        return self.coach < config.BENCH_THRESHOLD


@dataclass
class Contract:
    club: str
    wage_per_match: int = 300
    seasons_left: int = 1


@dataclass
class TeamRecord:
    name: str
    abbrev: str
    strength: int = 50  # AI quality 0-100
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    points_for: int = 0
    points_against: int = 0
    ladder_points: int = 0

    @property
    def diff(self) -> int:
        return self.points_for - self.points_against

    def record_result(self, scored: int, conceded: int) -> None:
        self.played += 1
        self.points_for += scored
        self.points_against += conceded
        if scored > conceded:
            self.won += 1
            self.ladder_points += config.POINTS_WIN
        elif scored == conceded:
            self.drawn += 1
            self.ladder_points += config.POINTS_DRAW
        else:
            self.lost += 1

    def record_bye(self) -> None:
        self.ladder_points += config.POINTS_BYE


def sort_ladder(teams: list[TeamRecord]) -> list[TeamRecord]:
    """NRL ladder order: points, then for/against differential, then points scored."""
    return sorted(teams, key=lambda t: (-t.ladder_points, -t.diff, -t.points_for))


@dataclass
class GameState:
    player: Player = field(default_factory=Player)
    contract: Contract | None = None
    teams: list[TeamRecord] = field(default_factory=list)
    round_no: int = 1
    season_no: int = 1

    @property
    def my_team(self) -> TeamRecord:
        return self.teams[self.player.team_idx]
