"""Headless tests for the pure-logic layer (no curses needed)."""

import unittest

from nrl import config
from nrl.minigames.base import Oscillator
from nrl.minigames.kick import POWER_SWEET_CENTER, judge_kick, sweet_spot_width
from nrl.models import Player, TeamRecord, sort_ladder


class TestOscillator(unittest.TestCase):
    def test_stays_in_range(self):
        osc = Oscillator(0, 100, speed=140)
        for _ in range(1000):
            v = osc.advance(0.033)
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 100)

    def test_bounces_at_edges(self):
        osc = Oscillator(0, 10, speed=100, start=9)
        osc.advance(0.05)  # +5 -> overshoots 10, reflects to 6 heading down
        self.assertEqual(osc.direction, -1)
        self.assertAlmostEqual(osc.value, 6.0)

    def test_handles_huge_overshoot(self):
        osc = Oscillator(0, 10, speed=1000)
        for _ in range(100):
            v = osc.advance(0.033)
            self.assertTrue(0 <= v <= 10)


class TestKickJudging(unittest.TestCase):
    def test_perfect_kick(self):
        r = judge_kick(POWER_SWEET_CENTER, 0.0, kicking_stat=40)
        self.assertTrue(r.success)
        self.assertEqual(r.quality, "perfect")

    def test_bad_power_fails(self):
        r = judge_kick(20.0, 0.0, kicking_stat=40)
        self.assertFalse(r.success)

    def test_bad_angle_fails(self):
        r = judge_kick(POWER_SWEET_CENTER, 45.0, kicking_stat=40)
        self.assertFalse(r.success)

    def test_higher_stat_widens_window(self):
        self.assertGreater(sweet_spot_width(90), sweet_spot_width(10))
        # A kick that misses for a rookie lands for a sharpshooter.
        edge_power = POWER_SWEET_CENTER + 12
        self.assertFalse(judge_kick(edge_power, 0, kicking_stat=10).success)
        self.assertTrue(judge_kick(edge_power, 0, kicking_stat=90).success)


class TestPlayer(unittest.TestCase):
    def test_adjust_clamps(self):
        p = Player()
        p.adjust("energy", +500)
        self.assertEqual(p.energy, 100)
        p.adjust("coach", -500)
        self.assertEqual(p.coach, 0)

    def test_benched_when_coach_hates_you(self):
        p = Player()
        p.coach = config.BENCH_THRESHOLD - 1
        self.assertTrue(p.is_benched)


class TestLadder(unittest.TestCase):
    def test_sorted_by_points_then_diff(self):
        a = TeamRecord("A", "AAA")
        b = TeamRecord("B", "BBB")
        c = TeamRecord("C", "CCC")
        a.record_result(30, 10)  # win, +20
        b.record_result(20, 10)  # win, +10
        c.record_result(10, 20)  # loss
        order = [t.name for t in sort_ladder([c, b, a])]
        self.assertEqual(order, ["A", "B", "C"])

    def test_bye_awards_points(self):
        t = TeamRecord("A", "AAA")
        t.record_bye()
        self.assertEqual(t.ladder_points, config.POINTS_BYE)
        self.assertEqual(t.played, 0)

    def test_draw(self):
        t = TeamRecord("A", "AAA")
        t.record_result(14, 14)
        self.assertEqual(t.drawn, 1)
        self.assertEqual(t.ladder_points, config.POINTS_DRAW)


if __name__ == "__main__":
    unittest.main()
