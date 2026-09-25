"""Level curve.

Reaching level L+1 from level L costs 100·(L+1) XP: 200 XP for level 2, 300 more
for level 3, 400 more for level 4 and so on. The cumulative total is therefore

    T(L) = 50·(L−1)·(L+2)          T(1)=0, T(2)=200, T(3)=500, T(10)=5 400, T(20)=20 900

Each level costs a constant 100 XP more than the last, so someone earning a steady
~250 XP a day gains a level every day or two in week one and one every week around
level 20. Levels keep coming without turning into a grind. The closed form can be
inverted exactly, so the level for any XP total is O(1) and needs no lookup table.
"""

import math
from dataclasses import dataclass

MAX_LEVEL = 100


def total_xp_for_level(level: int) -> int:
    """Cumulative XP needed to *reach* `level`."""
    if level <= 1:
        return 0
    return 50 * (level - 1) * (level + 2)


def xp_to_next(level: int) -> int:
    return total_xp_for_level(level + 1) - total_xp_for_level(level)


def level_for_xp(total_xp: int) -> int:
    if total_xp <= 0:
        return 1
    # Solve 50(L² + L − 2) = T for L, then correct any floating-point drift.
    level = int((-1 + math.sqrt(9 + 0.08 * total_xp)) / 2)
    while level < MAX_LEVEL and total_xp_for_level(level + 1) <= total_xp:
        level += 1
    while level > 1 and total_xp_for_level(level) > total_xp:
        level -= 1
    return max(1, min(level, MAX_LEVEL))


@dataclass(frozen=True)
class LevelProgress:
    level: int
    total_xp: int
    level_floor: int  # cumulative XP where this level started
    xp_into_level: int
    xp_for_level: int  # size of this level
    progress: float  # 0..1

    @property
    def xp_remaining(self) -> int:
        return self.xp_for_level - self.xp_into_level


def progress_for(total_xp: int) -> LevelProgress:
    level = level_for_xp(total_xp)
    floor = total_xp_for_level(level)
    size = xp_to_next(level)
    into = total_xp - floor
    if level >= MAX_LEVEL:
        return LevelProgress(level, total_xp, floor, into, into or 1, 1.0)
    return LevelProgress(level, total_xp, floor, into, size, round(into / size, 4))
