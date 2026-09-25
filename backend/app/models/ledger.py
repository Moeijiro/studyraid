import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.models._types import str_enum


class LedgerSource(enum.StrEnum):
    QUEST = "quest"
    FOCUS = "focus"
    ACHIEVEMENT = "achievement"
    CHALLENGE = "challenge"
    SHOP = "shop"


class LedgerEntry(Base):
    """Append-only record of every XP and coin change. The source of truth for
    totals, weekly XP, charts, streak days and party contribution.

    `source_ref` is unique per user ("quest:42", "achievement:first_blood"), so a
    reward can't be paid twice even if a request is retried or raced.
    """

    __tablename__ = "ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "source_ref"),
        Index("ix_ledger_user_date", "user_id", "local_date"),
        Index("ix_ledger_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[LedgerSource] = mapped_column(str_enum(LedgerSource))
    source_ref: Mapped[str] = mapped_column(String(80))
    xp: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    # Counts towards the daily streak (quest completion, focus session >= 10 min).
    counts_for_streak: Mapped[bool] = mapped_column(default=False)
    local_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class StreakFreeze(Base):
    __tablename__ = "streak_freezes"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
