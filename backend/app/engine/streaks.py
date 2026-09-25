"""Streaks from a set of active days.

A day is *active* when the user did something meaningful on it in their own time
zone: completed a quest, or completed a focus session of at least 10 minutes.
A streak freeze covers one missed day. It keeps the streak alive but doesn't add
to it.

The streak is computed from recorded activity every time, not kept as a running
counter, so it can't drift out of sync with the history it summarises.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

_DAY = timedelta(days=1)


@dataclass(frozen=True)
class StreakInfo:
    current: int
    longest: int
    active_today: bool
    # The streak is alive but today isn't done yet; it breaks at local midnight.
    at_risk: bool


def _run_ending(day: date, active: set[date], frozen: set[date]) -> int:
    count = 0
    while day in active or day in frozen:
        if day in active:
            count += 1
        day -= _DAY
    return count


def compute_streak(active_days: Iterable[date], today: date, frozen_days: Iterable[date] = ()) -> StreakInfo:
    active = {d for d in active_days if d <= today}
    frozen = {d for d in frozen_days if d <= today} - active

    active_today = today in active
    if active_today:
        current = _run_ending(today, active, frozen)
    elif (today - _DAY) in active or (today - _DAY) in frozen:
        current = _run_ending(today - _DAY, active, frozen)
    else:
        current = 0

    longest = 0
    run = 0
    previous: date | None = None
    for day in sorted(active | frozen):
        if previous is None or day - previous != _DAY:
            run = 0
        if day in active:
            run += 1
        longest = max(longest, run)
        previous = day

    return StreakInfo(current=current, longest=max(longest, current), active_today=active_today, at_risk=current > 0 and not active_today)


def missed_yesterday(active_days: set[date], frozen_days: set[date], today: date) -> bool:
    """True when yesterday broke a streak that a freeze could still rescue."""
    yesterday = today - _DAY
    if yesterday in active_days or yesterday in frozen_days:
        return False
    return _run_ending(yesterday - _DAY, active_days, frozen_days) > 0
