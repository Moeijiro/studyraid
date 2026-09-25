"""Spending coins. There is one item: a streak freeze, which covers one missed day."""

import secrets
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date
from app.core.errors import Conflict
from app.engine.streaks import missed_yesterday
from app.models import LedgerSource, StreakFreeze, User
from app.repositories import ledger as ledger_repo
from app.services import notifications, progression

STREAK_FREEZE_PRICE = 150
MAX_FREEZES_HELD = 2


async def buy_streak_freeze(session: AsyncSession, user: User, now: datetime) -> User:
    if user.streak_freezes >= MAX_FREEZES_HELD:
        raise Conflict(f"You can hold at most {MAX_FREEZES_HELD} streak freezes.", code="freeze_limit")
    if user.coins < STREAK_FREEZE_PRICE:
        raise Conflict("Not enough coins.", code="insufficient_coins")
    await progression.award(
        session,
        user,
        source=LedgerSource.SHOP,
        ref=f"shop:freeze:{secrets.token_hex(8)}",
        xp=0,
        coins=-STREAK_FREEZE_PRICE,
        now=now,
        detail={"item": "streak_freeze"},
    )
    user.streak_freezes += 1
    return user


async def apply_freeze_if_needed(session: AsyncSession, user: User, now: datetime) -> bool:
    """Scheduler job: if yesterday broke a live streak and a freeze is held, spend it."""
    if user.streak_freezes <= 0:
        return False
    today = local_date(now, user.timezone)
    active = await ledger_repo.active_days(session, user.id)
    frozen = await ledger_repo.frozen_days(session, user.id)
    if not missed_yesterday(active, frozen, today):
        return False
    yesterday = today - timedelta(days=1)
    session.add(StreakFreeze(user_id=user.id, day=yesterday, created_at=now))
    user.streak_freezes -= 1
    info = await progression.streak_for(session, user, today)
    await notifications.notify(
        session,
        user.id,
        kind="streak",
        title="🧊 A streak freeze saved your streak",
        body=f"Yesterday was covered. Your {info.current}-day streak is still alive.",
        link="/dashboard",
        dedupe_key=f"freeze:{yesterday.isoformat()}",
        now=now,
    )
    return True
