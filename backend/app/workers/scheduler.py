"""Background jobs.

Runs inside the API process by default (WORKER_ENABLED=true), or on its own with
`python -m app.workers.scheduler` when the API runs several replicas. Every job
is idempotent: state changes are conditional and notifications carry dedupe
keys, so overlapping runs never double-notify.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date, local_hour, utcnow
from app.core.config import get_settings
from app.db import session as db
from app.db.uow import commit
from app.models import User
from app.repositories import quests as quest_repo
from app.services import challenges, notifications, progression, quests, shop

log = logging.getLogger(__name__)

STREAK_REMINDER_HOUR = 19  # local time


async def remind_due_soon(session: AsyncSession, now: datetime) -> int:
    sent = 0
    users: dict[int, User] = {}
    for quest in await quest_repo.open_due_between(session, now, now + timedelta(hours=24)):
        user = users.get(quest.user_id) or await session.get(User, quest.user_id)
        if user is None or quest.due_at is None:
            continue
        users[user.id] = user
        when = "today" if local_date(quest.due_at, user.timezone) == local_date(now, user.timezone) else "tomorrow"
        note = await notifications.notify(
            session,
            user.id,
            kind="due_soon",
            title=f"Your {quest.subject} quest is due {when}",
            body=quest.title,
            link="/quests",
            dedupe_key=f"due_soon:{quest.id}",
            now=now,
        )
        sent += note is not None
    return sent


async def streak_jobs(session: AsyncSession, now: datetime) -> None:
    for user in await session.scalars(select(User)):
        await shop.apply_freeze_if_needed(session, user, now)
        today = local_date(now, user.timezone)
        info = await progression.streak_for(session, user, today)
        if info.at_risk and local_hour(now, user.timezone) >= STREAK_REMINDER_HOUR:
            await notifications.notify(
                session,
                user.id,
                kind="streak",
                title=f"🔥 Your {info.current}-day streak ends at midnight",
                body="Finish one quest or a focus session to keep it.",
                link="/quests",
                dedupe_key=f"streak_risk:{today.isoformat()}",
                now=now,
            )


async def run_once(now: datetime | None = None) -> None:
    now = now or utcnow()
    async with db.SessionLocal() as session:
        expired = await quests.expire_overdue(session, now)
        due = await remind_due_soon(session, now)
        await streak_jobs(session, now)
        settled = await challenges.settle_expired(session, now)
        await commit(session)
    if expired or due or settled:
        log.info("scheduler: %s expired, %s reminders, %s challenges settled", expired, due, settled)


async def run_forever(interval: float) -> None:
    while True:
        try:
            await run_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # keep the loop alive; the next tick retries
            log.exception("scheduler tick failed")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever(get_settings().worker_interval_seconds))
