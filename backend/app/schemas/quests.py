from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.engine.rewards import Difficulty
from app.models import Priority, QuestStatus
from app.schemas.common import AwareDatetime, Input, Schema

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Subject = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class QuestCreate(Input):
    title: Title
    subject: Subject
    difficulty: Difficulty = Difficulty.NORMAL
    description: Description = ""
    priority: Priority = Priority.NORMAL
    estimated_minutes: int | None = Field(default=None, ge=5, le=600)
    due_at: AwareDatetime | None = None


class QuestUpdate(Input):
    title: Title | None = None
    subject: Subject | None = None
    difficulty: Difficulty | None = None
    description: Description | None = None
    priority: Priority | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=600)
    due_at: AwareDatetime | None = None


class RewardPreviewIn(Input):
    difficulty: Difficulty
    estimated_minutes: int | None = Field(default=None, ge=5, le=600)


class QuestOut(Schema):
    id: int
    title: str
    description: str
    subject: str
    difficulty: Difficulty
    priority: Priority
    status: QuestStatus
    estimated_minutes: int | None
    due_at: datetime | None
    base_xp: int
    xp_awarded: int | None
    coins_awarded: int | None
    created_at: datetime
    started_at: datetime | None
    closed_at: datetime | None


class QuestPage(Schema):
    items: list[QuestOut]
    total: int


class RewardLine(Schema):
    label: str
    xp: int


class AchievementBrief(Schema):
    code: str
    name: str
    icon: str
    tier: str


class LevelOut(Schema):
    level: int
    total_xp: int
    xp_into_level: int
    xp_for_level: int
    progress: float


class CompletionOut(Schema):
    quest: QuestOut
    xp: int
    coins: int
    breakdown: list[RewardLine]
    level_before: int
    level: LevelOut
    streak: int
    achievements: list[AchievementBrief]
