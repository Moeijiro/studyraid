"""How much a piece of work is worth.

All rewards are computed on the server from facts it controls: difficulty, the
estimate given when the quest was created, the completion time against the due
date, and the XP already earned today. Clients never send an XP value.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class Difficulty(enum.StrEnum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    LEGENDARY = "legendary"


DIFFICULTY_BASE = {Difficulty.EASY: 20, Difficulty.NORMAL: 40, Difficulty.HARD: 75, Difficulty.LEGENDARY: 150}

EFFORT_XP_PER_MINUTE = 0.3
EFFORT_MINUTES_CAP = 240  # a four-hour estimate earns the maximum effort bonus

EARLY_BONUS = 0.10  # finished a full day before the deadline
EARLY_THRESHOLD = timedelta(hours=24)
LATE_FACTOR = 0.5  # finished inside the grace window after the deadline
LATE_GRACE = timedelta(hours=24)  # after this the scheduler marks the quest expired

STREAK_BONUS_PER_DAY = 0.02
STREAK_BONUS_CAP = 0.20  # reached at a 10-day streak

# Diminishing returns: past this much quest XP in one day, extra XP counts at 25%.
# Stops "create 200 quests, tick them all" from being worth more than real work.
DAILY_QUEST_SOFT_CAP = 600
OVER_CAP_FACTOR = 0.25

FOCUS_MIN_MINUTES = 10  # shorter sessions are recorded but earn nothing
FOCUS_MINUTES_PER_XP = 2  # one XP per two finished minutes
FOCUS_DAILY_REWARDED_MINUTES = 240

ACHIEVEMENT_XP = {"bronze": 25, "silver": 50, "gold": 100}
COINS_PER_XP = 0.1


def base_quest_xp(difficulty: Difficulty, estimated_minutes: int | None) -> int:
    effort = min(max(estimated_minutes or 0, 0), EFFORT_MINUTES_CAP)
    return DIFFICULTY_BASE[difficulty] + round(effort * EFFORT_XP_PER_MINUTE)


def coins_for(xp: int) -> int:
    return max(0, int(xp * COINS_PER_XP))


@dataclass(frozen=True)
class Reward:
    xp: int
    coins: int
    lines: list[tuple[str, int]] = field(default_factory=list)  # human-readable breakdown for the UI


def quest_reward(
    *,
    base_xp: int,
    completed_at: datetime,
    due_at: datetime | None,
    streak_days: int,
    quest_xp_earned_today: int,
) -> Reward:
    lines: list[tuple[str, int]] = [("Base", base_xp)]
    amount = float(base_xp)

    if due_at is not None:
        if completed_at > due_at:
            penalty = -round(amount * (1 - LATE_FACTOR))
            lines.append(("Late", penalty))
            amount += penalty
        elif due_at - completed_at >= EARLY_THRESHOLD:
            bonus = round(amount * EARLY_BONUS)
            lines.append(("Early finish", bonus))
            amount += bonus

    streak_mult = min(streak_days * STREAK_BONUS_PER_DAY, STREAK_BONUS_CAP)
    if streak_mult > 0:
        bonus = round(amount * streak_mult)
        lines.append((f"Streak ×{1 + streak_mult:.2f}", bonus))
        amount += bonus

    allowance = max(0, DAILY_QUEST_SOFT_CAP - quest_xp_earned_today)
    if amount > allowance:
        over = amount - allowance
        reduction = -round(over * (1 - OVER_CAP_FACTOR))
        lines.append(("Daily soft cap", reduction))
        amount += reduction

    xp = max(1, round(amount))
    return Reward(xp=xp, coins=coins_for(xp), lines=lines)


def focus_reward(*, minutes: int, rewarded_minutes_today: int) -> Reward:
    if minutes < FOCUS_MIN_MINUTES:
        return Reward(xp=0, coins=0, lines=[("Too short to count", 0)])
    eligible = max(0, min(minutes, FOCUS_DAILY_REWARDED_MINUTES - rewarded_minutes_today))
    xp = eligible // FOCUS_MINUTES_PER_XP
    lines = [("Focus", xp)]
    if eligible < minutes:
        lines.append(("Daily focus cap reached", 0))
    return Reward(xp=xp, coins=coins_for(xp), lines=lines)
