"""Quest lifecycle: planned → active → completed | failed | expired."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date
from app.core.errors import AppError, Conflict, NotFound
from app.db.uow import emit
from app.engine import rewards
from app.engine.achievements import AchievementDef
from app.engine.progression import level_for_xp
from app.engine.rewards import Difficulty, Reward
from app.models import LedgerSource, Priority, Quest, QuestStatus, User
from app.repositories import ledger as ledger_repo
from app.repositories import quests as quest_repo
from app.services import achievements, challenges, notifications, progression

MAX_OPEN_QUESTS = 200


@dataclass
class QuestInput:
    title: str
    subject: str
    difficulty: Difficulty
    description: str = ""
    priority: Priority = Priority.NORMAL
    estimated_minutes: int | None = None
    due_at: datetime | None = None


@dataclass
class CompletionResult:
    quest: Quest
    reward: Reward
    level_before: int
    level_after: int
    streak: int
    achievements: list[AchievementDef] = field(default_factory=list)


async def get(session: AsyncSession, user: User, quest_id: int) -> Quest:
    quest = await quest_repo.get_owned(session, user.id, quest_id)
    if quest is None:
        raise NotFound("Quest not found.")
    return quest


def _check_due(due_at: datetime | None, now: datetime) -> None:
    if due_at is not None and due_at <= now:
        raise AppError(
            "The due date must be in the future.",
            code="invalid_due_date",
            details=[{"field": "due_at", "message": "must be in the future"}],
        )


async def create(session: AsyncSession, user: User, data: QuestInput, now: datetime) -> Quest:
    _check_due(data.due_at, now)
    open_count = await session.scalar(
        select(func.count()).select_from(Quest).where(Quest.user_id == user.id, Quest.status.in_(quest_repo.OPEN))
    )
    if (open_count or 0) >= MAX_OPEN_QUESTS:
        raise Conflict(f"You can have at most {MAX_OPEN_QUESTS} open quests. Finish or remove some first.")
    quest = Quest(
        user_id=user.id,
        title=data.title,
        description=data.description,
        subject=data.subject,
        difficulty=data.difficulty,
        priority=data.priority,
        estimated_minutes=data.estimated_minutes,
        due_at=data.due_at,
        base_xp=rewards.base_quest_xp(data.difficulty, data.estimated_minutes),
        status=QuestStatus.PLANNED,
        created_at=now,
        updated_at=now,
    )
    session.add(quest)
    await session.flush()
    return quest


def _require_open(quest: Quest) -> None:
    if not quest.status.is_open:
        raise Conflict(f"This quest is already {quest.status.value}.", code="quest_closed")


async def update(session: AsyncSession, quest: Quest, changes: dict[str, Any], now: datetime) -> Quest:
    _require_open(quest)
    if "due_at" in changes:
        _check_due(changes["due_at"], now)
    for key, value in changes.items():
        setattr(quest, key, value)
    quest.base_xp = rewards.base_quest_xp(quest.difficulty, quest.estimated_minutes)
    quest.updated_at = now
    return quest


async def delete(session: AsyncSession, quest: Quest) -> None:
    if quest.status == QuestStatus.COMPLETED:
        # Completed quests back the XP ledger and the stats; they stay as history.
        raise Conflict("Completed quests are part of your history and can't be deleted.", code="quest_closed")
    await session.delete(quest)


async def start(session: AsyncSession, quest: Quest, now: datetime) -> Quest:
    if quest.status != QuestStatus.PLANNED:
        raise Conflict("Only planned quests can be started.", code="invalid_transition")
    quest.status = QuestStatus.ACTIVE
    quest.started_at = now
    quest.updated_at = now
    return quest


async def abandon(session: AsyncSession, quest: Quest, now: datetime) -> Quest:
    _require_open(quest)
    quest.status = QuestStatus.FAILED
    quest.closed_at = now
    quest.updated_at = now
    return quest


async def complete(session: AsyncSession, user: User, quest: Quest, now: datetime) -> CompletionResult:
    _require_open(quest)
    if quest.due_at is not None and now > quest.due_at + rewards.LATE_GRACE:
        # The scheduler marks it expired; completing it is refused either way.
        raise Conflict("This quest expired: its deadline and grace period have passed.", code="quest_expired")

    today = local_date(now, user.timezone)
    streak_before = await progression.streak_for(session, user, today)
    earned_today = await ledger_repo.xp_on(session, user.id, today, LedgerSource.QUEST)
    reward = rewards.quest_reward(
        base_xp=quest.base_xp,
        completed_at=now,
        due_at=quest.due_at,
        streak_days=streak_before.current,
        quest_xp_earned_today=earned_today,
    )

    quest.status = QuestStatus.COMPLETED
    quest.closed_at = now
    quest.updated_at = now
    quest.xp_awarded = reward.xp
    quest.coins_awarded = reward.coins
    await session.flush()

    level_before = progress_level(user)
    await progression.award(
        session,
        user,
        source=LedgerSource.QUEST,
        ref=f"quest:{quest.id}",
        xp=reward.xp,
        coins=reward.coins,
        now=now,
        counts_for_streak=True,
        detail={"title": quest.title, "subject": quest.subject, "difficulty": quest.difficulty.value, "lines": reward.lines},
    )
    streak = await progression.after_streak_activity(session, user, now)
    unlocked = await achievements.check(session, user, now)
    await challenges.on_activity(session, user, now)
    emit(session, user.id, "quest_completed", quest_id=quest.id, xp=reward.xp)
    return CompletionResult(quest, reward, level_before, progress_level(user), streak.current, unlocked)


def progress_level(user: User) -> int:
    return level_for_xp(user.total_xp)


async def expire_overdue(session: AsyncSession, now: datetime) -> int:
    """Scheduler job: open quests past deadline + grace become expired."""
    overdue = await quest_repo.open_due_before(session, now - rewards.LATE_GRACE)
    for quest in overdue:
        quest.status = QuestStatus.EXPIRED
        quest.closed_at = now
        quest.updated_at = now
        await notifications.notify(
            session,
            quest.user_id,
            kind="quest_expired",
            title=f"Quest expired: {quest.title}",
            body="The deadline and 24-hour grace period passed.",
            link="/quests",
            dedupe_key=f"expired:{quest.id}",
            now=now,
        )
    return len(overdue)
