"""Achievement definitions and the rule that unlocks them.

Every achievement is a threshold on one metric of `ActivityStats`, and those
stats are aggregated from real activity rows (quests, focus sessions, streak days,
party membership). There are no hand-granted badges, and the same definition gives
the UI its progress bar ("32 / 50 quests").
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

Tier = Literal["bronze", "silver", "gold"]


@dataclass(frozen=True)
class ActivityStats:
    quests_completed: int = 0
    legendary_completed: int = 0
    early_completions: int = 0
    night_owl_completions: int = 0
    early_bird_completions: int = 0
    subjects_completed: int = 0
    focus_sessions: int = 0
    focus_minutes: int = 0
    longest_focus_minutes: int = 0
    longest_streak: int = 0
    level: int = 1
    parties_joined: int = 0
    challenges_completed: int = 0


@dataclass(frozen=True)
class AchievementDef:
    code: str
    name: str
    description: str
    icon: str  # lucide icon name, resolved by the frontend
    tier: Tier
    metric: str
    target: int

    def value(self, stats: ActivityStats) -> int:
        return int(getattr(stats, self.metric))

    def is_met(self, stats: ActivityStats) -> bool:
        return self.value(stats) >= self.target


ACHIEVEMENTS: tuple[AchievementDef, ...] = (
    AchievementDef("first_blood", "First Blood", "Complete your first quest.", "sword", "bronze", "quests_completed", 1),
    AchievementDef("adventurer", "Adventurer", "Complete 10 quests.", "map", "bronze", "quests_completed", 10),
    AchievementDef("scholar", "Scholar", "Complete 50 quests.", "graduation-cap", "silver", "quests_completed", 50),
    AchievementDef("archmage", "Archmage", "Complete 150 quests.", "wand", "gold", "quests_completed", 150),
    AchievementDef("boss_slayer", "Boss Slayer", "Complete a Legendary quest.", "skull", "silver", "legendary_completed", 1),
    AchievementDef("dragon_hunter", "Dragon Hunter", "Complete 5 Legendary quests.", "flame-kindling", "gold", "legendary_completed", 5),
    AchievementDef("locked_in", "Locked In", "Complete 5 focus sessions.", "lock", "bronze", "focus_sessions", 5),
    AchievementDef("deep_work", "Deep Work", "Focus for 10 hours in total.", "brain", "silver", "focus_minutes", 600),
    AchievementDef(
        "marathon", "Marathon", "Finish a single focus session of 90 minutes or more.", "timer", "silver", "longest_focus_minutes", 90
    ),
    AchievementDef("no_days_off", "No Days Off", "Keep a 7-day streak.", "flame", "silver", "longest_streak", 7),
    AchievementDef("unbreakable", "Unbreakable", "Keep a 30-day streak.", "shield", "gold", "longest_streak", 30),
    AchievementDef("night_owl", "Night Owl", "Complete a quest between 23:00 and 04:00.", "moon", "bronze", "night_owl_completions", 1),
    AchievementDef(
        "early_bird", "Early Bird", "Complete a quest between 05:00 and 07:00.", "sunrise", "bronze", "early_bird_completions", 1
    ),
    AchievementDef(
        "ahead_of_schedule",
        "Ahead of Schedule",
        "Finish 10 quests at least a day before they're due.",
        "calendar-check",
        "silver",
        "early_completions",
        10,
    ),
    AchievementDef("polymath", "Polymath", "Complete quests in 5 different subjects.", "shapes", "silver", "subjects_completed", 5),
    AchievementDef("double_digits", "Double Digits", "Reach level 10.", "chevrons-up", "silver", "level", 10),
    AchievementDef("party_up", "Party Up", "Create or join a study party.", "users", "bronze", "parties_joined", 1),
    AchievementDef("raid_cleared", "Raid Cleared", "Help your party complete a challenge.", "trophy", "silver", "challenges_completed", 1),
)

BY_CODE = {a.code: a for a in ACHIEVEMENTS}


def newly_unlocked(stats: ActivityStats, already: Iterable[str]) -> list[AchievementDef]:
    owned = set(already)
    return [a for a in ACHIEVEMENTS if a.code not in owned and a.is_met(stats)]


def is_night_owl_hour(hour: int) -> bool:
    return hour >= 23 or hour < 4


def is_early_bird_hour(hour: int) -> bool:
    return 5 <= hour < 7
