from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LedgerEntry, LedgerSource, StreakFreeze


async def exists(session: AsyncSession, user_id: int, source_ref: str) -> bool:
    found = await session.scalar(select(LedgerEntry.id).where(LedgerEntry.user_id == user_id, LedgerEntry.source_ref == source_ref))
    return found is not None


async def xp_on(session: AsyncSession, user_id: int, day: date, source: LedgerSource | None = None) -> int:
    q = select(func.coalesce(func.sum(LedgerEntry.xp), 0)).where(LedgerEntry.user_id == user_id, LedgerEntry.local_date == day)
    if source is not None:
        q = q.where(LedgerEntry.source == source)
    return int(await session.scalar(q) or 0)


async def xp_between_dates(session: AsyncSession, user_id: int, start: date, end: date) -> int:
    q = select(func.coalesce(func.sum(LedgerEntry.xp), 0)).where(
        LedgerEntry.user_id == user_id, LedgerEntry.local_date >= start, LedgerEntry.local_date <= end
    )
    return int(await session.scalar(q) or 0)


async def xp_by_day(session: AsyncSession, user_id: int, start: date, end: date) -> dict[date, int]:
    rows = await session.execute(
        select(LedgerEntry.local_date, func.sum(LedgerEntry.xp))
        .where(LedgerEntry.user_id == user_id, LedgerEntry.local_date >= start, LedgerEntry.local_date <= end)
        .group_by(LedgerEntry.local_date)
    )
    return {d: int(x or 0) for d, x in rows.all()}


async def active_days(session: AsyncSession, user_id: int) -> set[date]:
    rows = await session.scalars(
        select(LedgerEntry.local_date).where(LedgerEntry.user_id == user_id, LedgerEntry.counts_for_streak.is_(True)).distinct()
    )
    return set(rows)


async def frozen_days(session: AsyncSession, user_id: int) -> set[date]:
    rows = await session.scalars(select(StreakFreeze.day).where(StreakFreeze.user_id == user_id))
    return set(rows)


async def xp_since(session: AsyncSession, user_ids: list[int], since: datetime, *, exclude_challenges: bool = False) -> dict[int, int]:
    if not user_ids:
        return {}
    q = (
        select(LedgerEntry.user_id, func.coalesce(func.sum(LedgerEntry.xp), 0))
        .where(LedgerEntry.user_id.in_(user_ids), LedgerEntry.created_at >= since)
        .group_by(LedgerEntry.user_id)
    )
    if exclude_challenges:
        q = q.where(LedgerEntry.source != LedgerSource.CHALLENGE)
    rows = await session.execute(q)
    return {uid: int(x) for uid, x in rows.all()}
