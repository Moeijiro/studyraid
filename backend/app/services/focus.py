"""Focus sessions with server-side timing.

The client shows a countdown, but only the server's clock decides how long a
session lasted. A session can only be completed once its planned time has
actually elapsed, and credit is capped at the planned length, so leaving a
timer running overnight earns nothing extra.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date
from app.core.errors import AppError, Conflict, NotFound
from app.db.uow import emit
from app.engine import rewards
from app.engine.achievements import AchievementDef
from app.engine.rewards import Reward
from app.models import FocusSession, FocusStatus, LedgerSource, Quest, User
from app.repositories import quests as quest_repo
from app.services import achievements, challenges, progression

MIN_PLANNED = 5
MAX_PLANNED = 180
# Browser timers drift and tabs sleep; allow completing a few seconds early.
EARLY_TOLERANCE = timedelta(seconds=20)
# An active session older than planned + this is treated as abandoned.
STALE_AFTER = timedelta(hours=1)


@dataclass
class FocusResult:
    session: FocusSession
    reward: Reward
    streak: int
    achievements: list[AchievementDef] = field(default_factory=list)


async def active_for(session: AsyncSession, user: User) -> FocusSession | None:
    return await session.scalar(select(FocusSession).where(FocusSession.user_id == user.id, FocusSession.status == FocusStatus.ACTIVE))


async def _owned(session: AsyncSession, user: User, focus_id: int) -> FocusSession:
    fs = await session.scalar(select(FocusSession).where(FocusSession.id == focus_id, FocusSession.user_id == user.id))
    if fs is None:
        raise NotFound("Focus session not found.")
    return fs


def _elapsed_minutes(fs: FocusSession, now: datetime) -> int:
    return max(0, int((now - fs.started_at).total_seconds() // 60))


async def start(session: AsyncSession, user: User, *, planned_minutes: int, quest_id: int | None, now: datetime) -> FocusSession:
    if not MIN_PLANNED <= planned_minutes <= MAX_PLANNED:
        raise AppError(f"Sessions are between {MIN_PLANNED} and {MAX_PLANNED} minutes.", code="invalid_duration")
    current = await active_for(session, user)
    if current is not None:
        if now - current.started_at > timedelta(minutes=current.planned_minutes) + STALE_AFTER:
            await _cancel(current, now, user)
        else:
            raise Conflict("You already have a focus session running.", code="focus_active")
    if quest_id is not None:
        quest = await quest_repo.get_owned(session, user.id, quest_id)
        if quest is None:
            raise NotFound("Quest not found.")
        if not quest.status.is_open:
            raise Conflict("You can only focus on an open quest.")
    fs = FocusSession(user_id=user.id, quest_id=quest_id, planned_minutes=planned_minutes, started_at=now, status=FocusStatus.ACTIVE)
    session.add(fs)
    await session.flush()
    emit(session, user.id, "focus_started", session_id=fs.id, planned_minutes=planned_minutes)
    return fs


async def _cancel(fs: FocusSession, now: datetime, user: User) -> None:
    fs.status = FocusStatus.CANCELLED
    fs.ended_at = now
    fs.actual_minutes = min(_elapsed_minutes(fs, now), fs.planned_minutes)
    fs.local_date = local_date(now, user.timezone)


async def cancel(session: AsyncSession, user: User, focus_id: int, now: datetime) -> FocusSession:
    fs = await _owned(session, user, focus_id)
    if fs.status != FocusStatus.ACTIVE:
        raise Conflict("This session has already ended.")
    await _cancel(fs, now, user)
    return fs


async def complete(session: AsyncSession, user: User, focus_id: int, now: datetime) -> FocusResult:
    fs = await _owned(session, user, focus_id)
    if fs.status != FocusStatus.ACTIVE:
        raise Conflict("This session has already ended.")
    planned = timedelta(minutes=fs.planned_minutes)
    if now - fs.started_at < planned - EARLY_TOLERANCE:
        remaining = int((planned - (now - fs.started_at)).total_seconds())
        raise Conflict("The session isn't over yet.", code="focus_not_finished", details={"remaining_seconds": remaining})

    today = local_date(now, user.timezone)
    minutes = fs.planned_minutes  # credit is capped at the plan
    rewarded_today = await session.scalar(
        select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
            FocusSession.user_id == user.id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.local_date == today,
            FocusSession.actual_minutes >= rewards.FOCUS_MIN_MINUTES,
        )
    )
    reward = rewards.focus_reward(minutes=minutes, rewarded_minutes_today=int(rewarded_today or 0))

    fs.status = FocusStatus.COMPLETED
    fs.ended_at = now
    fs.actual_minutes = minutes
    fs.xp_awarded = reward.xp
    fs.local_date = today
    await session.flush()

    unlocked: list[AchievementDef] = []
    streak = 0
    if minutes >= rewards.FOCUS_MIN_MINUTES:
        await progression.award(
            session,
            user,
            source=LedgerSource.FOCUS,
            ref=f"focus:{fs.id}",
            xp=reward.xp,
            coins=reward.coins,
            now=now,
            counts_for_streak=True,
            detail={"minutes": minutes, "quest_id": fs.quest_id},
        )
        streak = (await progression.after_streak_activity(session, user, now)).current
        unlocked = await achievements.check(session, user, now)
        await challenges.on_activity(session, user, now)
    emit(session, user.id, "focus_completed", session_id=fs.id, minutes=minutes, xp=reward.xp)
    return FocusResult(fs, reward, streak, unlocked)


async def summary(session: AsyncSession, user: User, now: datetime) -> dict[str, int]:
    today = local_date(now, user.timezone)
    week_start = today - timedelta(days=today.weekday())
    completed = (FocusSession.user_id == user.id, FocusSession.status == FocusStatus.COMPLETED)

    async def agg(*conds: object) -> tuple[int, int]:
        row = (
            await session.execute(select(func.count(), func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(*completed, *conds))
        ).one()  # type: ignore[arg-type]
        return int(row[0]), int(row[1])

    today_n, today_m = await agg(FocusSession.local_date == today)
    week_n, week_m = await agg(FocusSession.local_date >= week_start)
    total_n, total_m = await agg()
    return {
        "today_sessions": today_n,
        "today_minutes": today_m,
        "week_sessions": week_n,
        "week_minutes": week_m,
        "total_sessions": total_n,
        "total_minutes": total_m,
    }


async def history(session: AsyncSession, user: User, limit: int = 20) -> list[tuple[FocusSession, str | None]]:
    rows = await session.execute(
        select(FocusSession, Quest.title)
        .outerjoin(Quest, Quest.id == FocusSession.quest_id)
        .where(FocusSession.user_id == user.id, FocusSession.status != FocusStatus.ACTIVE)
        .order_by(FocusSession.started_at.desc())
        .limit(limit)
    )
    return [(fs, title) for fs, title in rows.all()]
