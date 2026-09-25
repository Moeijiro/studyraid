"""Paying out XP and coins through the ledger, and what follows from it (level-ups)."""

from datetime import date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date, week_start
from app.db.uow import emit
from app.engine.progression import level_for_xp, progress_for
from app.engine.streaks import StreakInfo, compute_streak
from app.models import LedgerEntry, LedgerSource, User
from app.repositories import ledger as ledger_repo
from app.services import notifications


def level_payload(total_xp: int) -> dict[str, Any]:
    p = progress_for(total_xp)
    return {
        "level": p.level,
        "total_xp": p.total_xp,
        "xp_into_level": p.xp_into_level,
        "xp_for_level": p.xp_for_level,
        "progress": p.progress,
    }


async def award(
    session: AsyncSession,
    user: User,
    *,
    source: LedgerSource,
    ref: str,
    xp: int,
    coins: int,
    now: datetime,
    counts_for_streak: bool = False,
    detail: dict[str, Any] | None = None,
) -> LedgerEntry | None:
    """Append a ledger entry and update the cached totals. Idempotent per `ref`."""
    if await ledger_repo.exists(session, user.id, ref):
        return None
    entry = LedgerEntry(
        user_id=user.id,
        source=source,
        source_ref=ref,
        xp=xp,
        coins=coins,
        counts_for_streak=counts_for_streak,
        local_date=local_date(now, user.timezone),
        created_at=now,
        detail=detail or {},
    )
    try:
        async with session.begin_nested():
            session.add(entry)
    except IntegrityError:  # lost a race with an identical request
        return None

    level_before = level_for_xp(user.total_xp)
    user.total_xp += xp
    user.coins += coins
    level_after = level_for_xp(user.total_xp)

    emit(session, user.id, "xp", amount=xp, coins=coins, source=source.value, balance=user.coins, level=level_payload(user.total_xp))
    if level_after > level_before:
        emit(session, user.id, "level_up", level=level_after)
        await notifications.notify(
            session,
            user.id,
            kind="level_up",
            title=f"You reached Level {level_after}",
            body=f"{progress_for(user.total_xp).xp_remaining:,} XP to Level {level_after + 1}.",
            link="/dashboard",
            dedupe_key=f"level:{level_after}",
            now=now,
        )
    return entry


async def streak_for(session: AsyncSession, user: User, today: date) -> StreakInfo:
    active = await ledger_repo.active_days(session, user.id)
    frozen = await ledger_repo.frozen_days(session, user.id)
    return compute_streak(active, today, frozen)


async def weekly_xp(session: AsyncSession, user: User, now: datetime) -> int:
    today = local_date(now, user.timezone)
    return await ledger_repo.xp_between_dates(session, user.id, week_start(today), today)


STREAK_MILESTONES = (3, 7, 14, 30, 50, 100, 200, 365)


async def after_streak_activity(session: AsyncSession, user: User, now: datetime) -> StreakInfo:
    """Called after anything that counts for the streak; announces milestones."""
    today = local_date(now, user.timezone)
    info = await streak_for(session, user, today)
    emit(session, user.id, "streak", current=info.current, longest=info.longest, active_today=info.active_today)
    if info.current in STREAK_MILESTONES:
        await notifications.notify(
            session,
            user.id,
            kind="streak",
            title=f"🔥 Your {info.current}-day streak is active",
            body="Keep it going tomorrow.",
            link="/dashboard",
            dedupe_key=f"streak_milestone:{info.current}:{today.isoformat()}",
            now=now,
        )
    return info
