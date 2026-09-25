import enum
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.models._types import str_enum


class FocusStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FocusSession(Base):
    __tablename__ = "focus_sessions"
    __table_args__ = (Index("ix_focus_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    quest_id: Mapped[int | None] = mapped_column(ForeignKey("quests.id", ondelete="SET NULL"), nullable=True)
    planned_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[FocusStatus] = mapped_column(str_enum(FocusStatus), default=FocusStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # Minutes the server measured, not what the client reported.
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    local_date: Mapped[date | None] = mapped_column(Date, nullable=True)
