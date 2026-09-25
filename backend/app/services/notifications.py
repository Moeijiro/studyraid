"""Internal notifications: stored, pushed live, idempotent per dedupe key."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.db.uow import emit
from app.models import Notification


def serialize(n: Notification) -> dict[str, object]:
    return {
        "id": n.id,
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "created_at": n.created_at.isoformat(),
        "read": n.read_at is not None,
    }


async def notify(
    session: AsyncSession,
    user_id: int,
    *,
    kind: str,
    title: str,
    body: str = "",
    link: str | None = None,
    dedupe_key: str | None = None,
    now: datetime,
) -> Notification | None:
    """Create a notification. Returns None if one with this dedupe key already exists."""
    if dedupe_key is not None:
        existing = await session.scalar(
            select(Notification.id).where(Notification.user_id == user_id, Notification.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return None
    note = Notification(user_id=user_id, kind=kind, title=title[:140], body=body[:400], link=link, dedupe_key=dedupe_key, created_at=now)
    try:
        async with session.begin_nested():  # a concurrent scheduler run may win the race
            session.add(note)
    except IntegrityError:
        return None
    emit(session, user_id, "notification", notification=serialize(note))
    return note


async def list_for(session: AsyncSession, user_id: int, *, limit: int = 30, unread_only: bool = False) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    rows = await session.scalars(q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit))
    return list(rows)


async def unread_count(session: AsyncSession, user_id: int) -> int:
    q = select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    return int(await session.scalar(q) or 0)


async def mark_read(session: AsyncSession, user_id: int, notification_id: int, now: datetime) -> Notification:
    note = await session.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id))
    if note is None:
        raise NotFound("Notification not found.")
    if note.read_at is None:
        note.read_at = now
    return note


async def mark_all_read(session: AsyncSession, user_id: int, now: datetime) -> None:
    await session.execute(update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).values(read_at=now))
