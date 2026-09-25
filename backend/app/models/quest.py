import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.engine.rewards import Difficulty
from app.models._types import str_enum


class QuestStatus(enum.StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"  # abandoned by the user
    EXPIRED = "expired"  # deadline plus grace window passed

    @property
    def is_open(self) -> bool:
        return self in (QuestStatus.PLANNED, QuestStatus.ACTIVE)


class Priority(enum.StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Quest(Base):
    __tablename__ = "quests"
    __table_args__ = (Index("ix_quests_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(40))
    difficulty: Mapped[Difficulty] = mapped_column(str_enum(Difficulty))
    priority: Mapped[Priority] = mapped_column(str_enum(Priority), default=Priority.NORMAL)
    status: Mapped[QuestStatus] = mapped_column(str_enum(QuestStatus), default=QuestStatus.PLANNED)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    base_xp: Mapped[int] = mapped_column(Integer)
    xp_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coins_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
