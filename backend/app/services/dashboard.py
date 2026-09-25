"""Everything the dashboard needs in one round trip."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date, local_midnight_utc
from app.models import Quest, User
from app.repositories import quests as quest_repo
from app.services import achievements, analytics, focus, notifications, parties, progression


async def summary(session: AsyncSession, user: User, now: datetime) -> dict[str, Any]:
    today = local_date(now, user.timezone)
    end_of_today = local_midnight_utc(today + timedelta(days=1), user.timezone)
    streak = await progression.streak_for(session, user, today)

    open_quests = list(await session.scalars(quest_repo.list_query(user.id, statuses=list(quest_repo.OPEN))))
    todays = [q for q in open_quests if q.status.value == "active" or (q.due_at is not None and q.due_at < end_of_today)]
    upcoming = [q for q in open_quests if q not in todays and q.due_at is not None and q.due_at < end_of_today + timedelta(days=7)]
    completed_today = list(
        await session.scalars(
            select(Quest)
            .where(Quest.user_id == user.id, Quest.status == "completed", Quest.closed_at >= local_midnight_utc(today, user.timezone))
            .order_by(Quest.closed_at.desc())
        )
    )

    stats = await analytics.overview(session, user, now, days=7)
    party_list = await parties.list_mine(session, user, now)
    active_focus = await focus.active_for(session, user)
    return {
        "level": progression.level_payload(user.total_xp),
        "coins": user.coins,
        "streak": {
            "current": streak.current,
            "longest": streak.longest,
            "active_today": streak.active_today,
            "at_risk": streak.at_risk,
            "freezes": user.streak_freezes,
        },
        "weekly_xp": await progression.weekly_xp(session, user, now),
        "today_quests": todays[:8],
        "completed_today": completed_today[:8],
        "upcoming_quests": upcoming[:6],
        "week": stats["series"],
        "focus": await focus.summary(session, user, now),
        "active_focus_id": active_focus.id if active_focus else None,
        "recent_achievements": await achievements.recent(session, user),
        "parties": party_list[:3],
        "unread_notifications": await notifications.unread_count(session, user.id),
    }
