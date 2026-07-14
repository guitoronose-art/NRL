"""Headless tests for fixtures, match planning, and the new mini-game logic."""

import random
import unittest

from nrl import config, season
from nrl.match_engine import effective, pick_moments, plan_match
from nrl.minigames.breakaway import FIELD_H, PLAYER_X, RUN_SECONDS, RunState
from nrl.minigames.pass_game import (
    DEFENDER_REACH, PassSetup, judge_pass, make_setup, trajectory_y,
)
from nrl.minigames.training import ZONE_HALF_WIDTH, judge_training
from nrl.models import Contract, GameState, Player, TeamRecord


def make_state() -> GameState:
    teams = [TeamRecord(name=n, abbrev=a, strength=50) for n, a in config.NRL_TEAMS]
    state = GameState(teams=teams)
    state.contract = Contract(club=teams[0].name)
    return state


class TestFixtures(unittest.TestCase):
    def setUp(self):
        self.fixtures = season.generate_fixtures(17, config.SEASON_ROUNDS)

    def test_right_number_of_rounds(self):
        self.assertEqual(len(self.fixtures), 27)

    def test_every_team_appears_once_per_round(self):
        for rnd in self.fixtures:
            seen = [t for pair in rnd for t in pair]
            teams = [t for t in seen if t != season.BYE]
            self.assertEqual(sorted(teams), list(range(17)))
            self.assertEqual(seen.count(season.BYE), 1)

    def test_opponent_lookup(self):
        opp = season.opponent_for(self.fixtures, 1, 0)
        self.assertIsNotNone(opp)
        # symmetric
        self.assertEqual(season.opponent_for(self.fixtures, 1, opp), 0)

    def test_everyone_gets_byes_across_season(self):
        bye_teams = [
            a for rnd in self.fixtures for a, b in rnd if b == season.BYE
        ]
        # 27 rounds of 17 teams: everyone byes at least once
        self.assertEqual(set(bye_teams), set(range(17)))

    def test_ai_round_updates_all_other_teams(self):
        state = make_state()
        state.player.team_idx = 0
        season.simulate_other_matches(state, self.fixtures, random.Random(7))
        played_or_bye = [
            t for i, t in enumerate(state.teams)
            if i != 0 and (t.played == 1 or t.ladder_points == config.POINTS_BYE)
        ]
        self.assertEqual(len(played_or_bye), 16)
        self.assertEqual(state.teams[0].played, 0)


class TestPassLogic(unittest.TestCase):
    def make(self) -> PassSetup:
        return PassSetup(player_y=8, player_x=3, defender_y=8, defender_x=30,
                         winger_y=8, winger_x=55)

    def test_flat_pass_through_defender_is_intercepted(self):
        r = judge_pass(self.make(), 0.0, passing_stat=50)
        self.assertTrue(r.intercepted)

    def test_lobbed_pass_over_defender_completes(self):
        s = self.make()
        s.defender_y = 8
        s.winger_y = 2
        # find an angle that clears X and lands near O
        for angle in range(5, 50):
            y_def = trajectory_y(s, angle, s.defender_x)
            y_wing = trajectory_y(s, angle, s.winger_x)
            if abs(y_def - s.defender_y) > DEFENDER_REACH and abs(y_wing - s.winger_y) < 1:
                r = judge_pass(s, angle, passing_stat=50)
                self.assertTrue(r.complete)
                return
        self.fail("no completing angle found - geometry broken")

    def test_wild_pass_is_wasted(self):
        s = self.make()
        s.winger_y = 2
        r = judge_pass(s, -50.0, passing_stat=50)  # fired at the ground away from everyone
        self.assertEqual(r.quality, "wasted")

    def test_make_setup_in_bounds(self):
        for seed in range(50):
            s = make_setup(random.Random(seed))
            self.assertTrue(0 <= s.defender_y < 16)
            self.assertTrue(0 <= s.winger_y < 16)


class TestBreakawayLogic(unittest.TestCase):
    def test_run_finishes_by_time(self):
        run = RunState(rng=random.Random(1))
        t = 0.0
        while not run.finished and t < 10:
            run.tick(0.033)
            t += 0.033
        self.assertTrue(run.finished)

    def test_collision_tackles(self):
        from nrl.minigames.breakaway import Defender
        run = RunState(rng=random.Random(1))
        run.defenders = [Defender(x=PLAYER_X + 0.5, y=run.player_y)]
        run.tick(0.001)
        self.assertTrue(run.tackled)

    def test_move_clamps_to_field(self):
        run = RunState(rng=random.Random(1))
        for _ in range(50):
            run.move(-1)
        self.assertEqual(run.player_y, 0)
        for _ in range(50):
            run.move(+1)
        self.assertEqual(run.player_y, FIELD_H - 1)


class TestTrainingLogic(unittest.TestCase):
    def test_gains_scale_with_accuracy(self):
        self.assertEqual(judge_training(50, 50), 3)
        self.assertEqual(judge_training(50 + ZONE_HALF_WIDTH * 0.5, 50), 2)
        self.assertEqual(judge_training(50 + ZONE_HALF_WIDTH * 0.9, 50), 1)
        self.assertEqual(judge_training(50 + ZONE_HALF_WIDTH * 2, 50), 0)


class TestMatchPlanning(unittest.TestCase):
    def test_plan_has_moments_in_range(self):
        state = make_state()
        for seed in range(20):
            events = plan_match(state, state.teams[1], random.Random(seed))
            moments = [e for e in events if e.kind == "moment"]
            lo, hi = config.MOMENTS_PER_MATCH
            self.assertTrue(lo <= len(moments) <= hi)
            self.assertEqual([e.minute for e in events], sorted(e.minute for e in events))

    def test_cold_teammates_reduce_pass_moments(self):
        rng_a, rng_b = random.Random(42), random.Random(42)
        warm, cold = Player(), Player()
        cold.teammates = config.COLD_SHOULDER_THRESHOLD - 10
        warm_passes = sum(
            pick_moments(warm, rng_a).count("pass") for _ in range(300)
        )
        cold_passes = sum(
            pick_moments(cold, rng_b).count("pass") for _ in range(300)
        )
        self.assertLess(cold_passes, warm_passes)

    def test_fatigue_halves_stats(self):
        self.assertEqual(effective(80, 0), 40)
        self.assertEqual(effective(80, 100), 80)


if __name__ == "__main__":
    unittest.main()
