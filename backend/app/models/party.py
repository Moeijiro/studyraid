import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.models._types import str_enum


class PartyRole(enum.StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class InviteStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class ChallengeMetric(enum.StrEnum):
    QUESTS_COMPLETED = "quests_completed"
    FOCUS_MINUTES = "focus_minutes"
    XP = "xp"


class ChallengeStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(200), default="")
    icon: Mapped[str] = mapped_column(String(24))
    hue: Mapped[int] = mapped_column(Integer, default=265)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PartyMember(Base):
    __tablename__ = "party_members"
    __table_args__ = (UniqueConstraint("party_id", "user_id"), Index("ix_party_members_user", "user_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[PartyRole] = mapped_column(str_enum(PartyRole), default=PartyRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PartyInvite(Base):
    __tablename__ = "party_invites"
    __table_args__ = (Index("ix_party_invites_invitee", "invitee_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id", ondelete="CASCADE"))
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[InviteStatus] = mapped_column(str_enum(InviteStatus), default=InviteStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class PartyChallenge(Base):
    __tablename__ = "party_challenges"
    __table_args__ = (Index("ix_party_challenges_party_status", "party_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id", ondelete="CASCADE"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(80))
    metric: Mapped[ChallengeMetric] = mapped_column(str_enum(ChallengeMetric))
    target: Mapped[int] = mapped_column(Integer)
    reward_xp: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[ChallengeStatus] = mapped_column(str_enum(ChallengeStatus), default=ChallengeStatus.ACTIVE)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
