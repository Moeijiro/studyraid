"""The level curve and reward formulas, tested as pure functions."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from app.engine import rewards
from app.engine.progression import MAX_LEVEL, level_for_xp, progress_for, total_xp_for_level, xp_to_next
from app.engine.rewards import Difficulty, base_quest_xp, focus_reward, quest_reward

T0 = datetime(2026, 3, 11, 12, tzinfo=UTC)


def test_curve_starts_gently_and_grows_by_100_per_level():
    assert [total_xp_for_level(lv) for lv in (1, 2, 3, 4, 5)] == [0, 200, 500, 900, 1400]
    steps = [xp_to_next(lv) for lv in range(1, 30)]
    assert all(b - a == 100 for a, b in pairwise(steps))


@pytest.mark.parametrize(("xp", "level"), [(0, 1), (199, 1), (200, 2), (499, 2), (500, 3), (5399, 9), (5400, 10)])
def test_level_boundaries(xp: int, level: int):
    assert level_for_xp(xp) == level


def test_closed_form_inverse_agrees_with_the_curve_at_every_level():
    for lv in range(1, MAX_LEVEL + 1):
        floor = total_xp_for_level(lv)
        assert level_for_xp(floor) == lv
        if lv > 1:
            assert level_for_xp(floor - 1) == lv - 1


def test_progress_within_level():
    p = progress_for(650)  # level 3 spans 500..900
    assert (p.level, p.xp_into_level, p.xp_for_level, p.xp_remaining) == (3, 150, 400, 250)
    assert p.progress == pytest.approx(0.375)


def test_base_xp_rewards_difficulty_and_capped_effort():
    assert base_quest_xp(Difficulty.EASY, None) == 20
    assert base_quest_xp(Difficulty.NORMAL, 60) == 40 + 18
    assert base_quest_xp(Difficulty.LEGENDARY, 10_000) == base_quest_xp(Difficulty.LEGENDARY, rewards.EFFORT_MINUTES_CAP)


def test_early_late_and_streak_modifiers():
    early = quest_reward(base_xp=100, completed_at=T0, due_at=T0 + timedelta(days=2), streak_days=0, quest_xp_earned_today=0)
    on_time = quest_reward(base_xp=100, completed_at=T0, due_at=T0 + timedelta(hours=2), streak_days=0, quest_xp_earned_today=0)
    late = quest_reward(base_xp=100, completed_at=T0, due_at=T0 - timedelta(hours=1), streak_days=0, quest_xp_earned_today=0)
    assert (early.xp, on_time.xp, late.xp) == (110, 100, 50)
    assert ("Early finish", 10) in early.lines


def test_streak_bonus_caps_at_twenty_percent():
    ten = quest_reward(base_xp=100, completed_at=T0, due_at=None, streak_days=10, quest_xp_earned_today=0)
    hundred = quest_reward(base_xp=100, completed_at=T0, due_at=None, streak_days=100, quest_xp_earned_today=0)
    assert ten.xp == hundred.xp == 120


def test_daily_soft_cap_applies_diminishing_returns():
    under = quest_reward(base_xp=100, completed_at=T0, due_at=None, streak_days=0, quest_xp_earned_today=0)
    straddling = quest_reward(base_xp=100, completed_at=T0, due_at=None, streak_days=0, quest_xp_earned_today=560)
    over = quest_reward(base_xp=100, completed_at=T0, due_at=None, streak_days=0, quest_xp_earned_today=5000)
    assert under.xp == 100
    assert straddling.xp == 40 + 15  # 40 XP of allowance left, the other 60 at 25%
    assert over.xp == 25
    assert over.coins == 2


def test_focus_reward_minimum_and_daily_cap():
    assert focus_reward(minutes=9, rewarded_minutes_today=0).xp == 0
    assert focus_reward(minutes=50, rewarded_minutes_today=0).xp == 25
    capped = focus_reward(minutes=50, rewarded_minutes_today=rewards.FOCUS_DAILY_REWARDED_MINUTES - 20)
    assert capped.xp == 10
    assert focus_reward(minutes=50, rewarded_minutes_today=10_000).xp == 0
