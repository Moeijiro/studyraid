from datetime import date, timedelta

from app.engine.achievements import ACHIEVEMENTS, ActivityStats, is_early_bird_hour, is_night_owl_hour, newly_unlocked
from app.engine.streaks import compute_streak, missed_yesterday

TODAY = date(2026, 3, 11)


def days(*offsets: int) -> set[date]:
    return {TODAY - timedelta(days=o) for o in offsets}


def test_no_activity_means_no_streak():
    s = compute_streak(set(), TODAY)
    assert (s.current, s.longest, s.active_today, s.at_risk) == (0, 0, False, False)


def test_streak_counts_back_from_today():
    s = compute_streak(days(0, 1, 2, 3), TODAY)
    assert (s.current, s.longest, s.active_today, s.at_risk) == (4, 4, True, False)


def test_streak_is_at_risk_until_today_is_done():
    s = compute_streak(days(1, 2, 3), TODAY)
    assert (s.current, s.at_risk) == (3, True)


def test_a_missed_day_breaks_the_streak_but_longest_is_kept():
    s = compute_streak(days(0, 1, 3, 4, 5, 6, 7), TODAY)
    assert (s.current, s.longest) == (2, 5)


def test_two_days_ago_is_too_late():
    assert compute_streak(days(2, 3, 4), TODAY).current == 0


def test_freeze_bridges_a_gap_without_adding_a_day():
    s = compute_streak(days(0, 1, 3, 4), TODAY, frozen_days=days(2))
    assert (s.current, s.longest) == (4, 4)


def test_future_dates_are_ignored():
    assert compute_streak(days(0, -1, -2), TODAY).current == 1


def test_missed_yesterday_only_when_a_streak_was_alive():
    assert missed_yesterday(days(2, 3), set(), TODAY)
    assert not missed_yesterday(days(1, 2), set(), TODAY)
    assert not missed_yesterday(set(), set(), TODAY)
    assert not missed_yesterday(days(2), days(1), TODAY)


def test_achievements_unlock_on_thresholds_and_only_once():
    stats = ActivityStats(quests_completed=10, legendary_completed=1, level=10)
    codes = {a.code for a in newly_unlocked(stats, [])}
    assert {"first_blood", "adventurer", "boss_slayer", "double_digits"} <= codes
    assert "scholar" not in codes
    assert newly_unlocked(stats, codes) == []


def test_every_achievement_reads_a_real_stat():
    stats = ActivityStats()
    for a in ACHIEVEMENTS:
        assert isinstance(a.value(stats), int), a.code


def test_night_owl_and_early_bird_windows():
    assert [h for h in range(24) if is_night_owl_hour(h)] == [0, 1, 2, 3, 23]
    assert [h for h in range(24) if is_early_bird_hour(h)] == [5, 6]
