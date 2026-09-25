"""Commit, then publish the live events the transaction produced."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.realtime.hub import hub

_OUTBOX = "outbox"


def emit(session: AsyncSession, recipient_id: int, event_type: str, /, **data: Any) -> None:
    session.info.setdefault(_OUTBOX, []).append((recipient_id, {"type": event_type, **data}))


async def commit(session: AsyncSession) -> None:
    await session.commit()
    events = session.info.pop(_OUTBOX, [])
    for user_id, event in events:
        hub.publish(user_id, event)


async def rollback(session: AsyncSession) -> None:
    await session.rollback()
    session.info.pop(_OUTBOX, None)
