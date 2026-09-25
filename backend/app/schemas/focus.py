from datetime import datetime

from pydantic import Field

from app.models import FocusStatus
from app.schemas.common import Input, Schema
from app.schemas.quests import AchievementBrief, LevelOut, RewardLine


class FocusStart(Input):
    planned_minutes: int = Field(ge=5, le=180)
    quest_id: int | None = None


class FocusOut(Schema):
    id: int
    quest_id: int | None
    planned_minutes: int
    status: FocusStatus
    started_at: datetime
    ended_at: datetime | None
    actual_minutes: int
    xp_awarded: int


class FocusCompleteOut(Schema):
    session: FocusOut
    xp: int
    coins: int
    breakdown: list[RewardLine]
    level: LevelOut
    streak: int
    achievements: list[AchievementBrief]
