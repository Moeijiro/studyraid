from datetime import datetime

from sqlalchemy import Select, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quest, QuestStatus

OPEN = (QuestStatus.PLANNED, QuestStatus.ACTIVE)


async def get_owned(session: AsyncSession, user_id: int, quest_id: int) -> Quest | None:
    """Ownership is part of the lookup: another user's quest is simply not found."""
    return await session.scalar(select(Quest).where(Quest.id == quest_id, Quest.user_id == user_id))


def list_query(
    user_id: int,
    *,
    statuses: list[QuestStatus] | None = None,
    subject: str | None = None,
    search: str | None = None,
) -> Select[tuple[Quest]]:
    q = select(Quest).where(Quest.user_id == user_id)
    if statuses:
        q = q.where(Quest.status.in_(statuses))
    if subject:
        q = q.where(Quest.subject == subject)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        q = q.where(or_(Quest.title.ilike(like, escape="\\"), Quest.description.ilike(like, escape="\\")))
    if statuses and not any(s.is_open for s in statuses):
        # History views: most recently closed first.
        return q.order_by(Quest.closed_at.desc(), Quest.id.desc())
    # Open quests: soonest deadline first (no deadline last), then newest.
    no_due_last = case((Quest.due_at.is_(None), 1), else_=0)
    return q.order_by(no_due_last, Quest.due_at, Quest.created_at.desc())


async def open_due_between(session: AsyncSession, start: datetime, end: datetime) -> list[Quest]:
    rows = await session.scalars(
        select(Quest).where(Quest.status.in_(OPEN), Quest.due_at.is_not(None), Quest.due_at > start, Quest.due_at <= end)
    )
    return list(rows)


async def open_due_before(session: AsyncSession, cutoff: datetime) -> list[Quest]:
    rows = await session.scalars(select(Quest).where(Quest.status.in_(OPEN), Quest.due_at.is_not(None), Quest.due_at < cutoff))
    return list(rows)
