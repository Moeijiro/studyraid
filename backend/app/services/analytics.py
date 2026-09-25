"""Personal statistics, aggregated from the ledger, quests and focus sessions.

Grouping uses the `local_date` stored on each ledger entry and focus session,
not SQL date functions, so the same queries run unchanged on SQLite and
PostgreSQL and days follow the user's own calendar.
"""

import calendar
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date, local_midnight_utc, week_start
from app.engine import rewards
from app.models import FocusSession, FocusStatus, Quest, QuestStatus, User
from app.repositories import ledger as ledger_repo

HEATMAP_THRESHOLDS = (1, 60, 150, 300)  # XP for intensity levels 1..4


def heat_level(xp: int) -> int:
    return sum(1 for t in HEATMAP_THRESHOLDS if xp >= t)


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


async def _focus_by_day(session: AsyncSession, user: User, start: date, end: date) -> dict[date, int]:
    rows = await session.execute(
        select(FocusSession.local_date, func.sum(FocusSession.actual_minutes))
        .where(
            FocusSession.user_id == user.id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.local_date >= start,
            FocusSession.local_date <= end,
        )
        .group_by(FocusSession.local_date)
    )
    return {d: int(m or 0) for d, m in rows.all() if d is not None}


async def heatmap(session: AsyncSession, user: User, now: datetime, weeks: int = 26) -> dict[str, Any]:
    today = local_date(now, user.timezone)
    start = week_start(today) - timedelta(weeks=weeks - 1)
    xp = await ledger_repo.xp_by_day(session, user.id, start, today)
    active = await ledger_repo.active_days(session, user.id)
    frozen = await ledger_repo.frozen_days(session, user.id)
    return {
        "start": start.isoformat(),
        "end": today.isoformat(),
        "thresholds": list(HEATMAP_THRESHOLDS),
        "days": [
            {"date": d.isoformat(), "xp": xp.get(d, 0), "level": heat_level(xp.get(d, 0)), "active": d in active, "frozen": d in frozen}
            for d in _days(start, today)
        ],
    }


async def overview(session: AsyncSession, user: User, now: datetime, days: int = 30) -> dict[str, Any]:
    today = local_date(now, user.timezone)
    start = today - timedelta(days=days - 1)
    window_start_utc = local_midnight_utc(start, user.timezone)

    xp = await ledger_repo.xp_by_day(session, user.id, start, today)
    focus = await _focus_by_day(session, user, start, today)

    closed = (
        await session.execute(
            select(Quest.status, Quest.subject, Quest.closed_at, Quest.xp_awarded).where(
                Quest.user_id == user.id,
                Quest.closed_at >= window_start_utc,
                Quest.status.in_([QuestStatus.COMPLETED, QuestStatus.FAILED, QuestStatus.EXPIRED]),
            )
        )
    ).all()
    completed = [(subj, local_date(at, user.timezone), xp_) for st, subj, at, xp_ in closed if st == QuestStatus.COMPLETED and at]
    quests_by_day = Counter(d for _, d, _ in completed)
    completion_rate = round(len(completed) / len(closed), 4) if closed else None

    series = [
        {"date": d.isoformat(), "xp": xp.get(d, 0), "focus_minutes": focus.get(d, 0), "quests": quests_by_day.get(d, 0)}
        for d in _days(start, today)
    ]

    weekday_xp: dict[int, list[int]] = defaultdict(list)
    for d in _days(start, today):
        weekday_xp[d.weekday()].append(xp.get(d, 0))
    weekday_avg = {wd: sum(v) / len(v) for wd, v in weekday_xp.items() if v}
    best_wd = max(weekday_avg, key=lambda wd: weekday_avg[wd]) if any(weekday_avg.values()) else None

    subjects: dict[str, dict[str, int]] = defaultdict(lambda: {"quests": 0, "xp": 0, "focus_minutes": 0})
    for subj, _, xp_ in completed:
        subjects[subj]["quests"] += 1
        subjects[subj]["xp"] += xp_ or 0
    focus_subjects = await session.execute(
        select(Quest.subject, func.sum(FocusSession.actual_minutes))
        .join(Quest, Quest.id == FocusSession.quest_id)
        .where(
            FocusSession.user_id == user.id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.local_date >= start,
            FocusSession.local_date <= today,
        )
        .group_by(Quest.subject)
    )
    for subj, minutes in focus_subjects.all():
        subjects[subj]["focus_minutes"] += int(minutes or 0)
    subject_rows = sorted(({"subject": s, **v} for s, v in subjects.items()), key=lambda r: (-r["xp"], -r["focus_minutes"]))

    this_week = week_start(today)
    week_starts = [this_week - timedelta(weeks=i) for i in range(7, -1, -1)]
    wxp = await ledger_repo.xp_by_day(session, user.id, week_starts[0], today)
    weekly = [
        {"week_start": ws.isoformat(), "xp": sum(v for d, v in wxp.items() if ws <= d < ws + timedelta(days=7))} for ws in week_starts
    ]

    sessions = await session.scalar(
        select(func.count())
        .select_from(FocusSession)
        .where(
            FocusSession.user_id == user.id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.local_date >= start,
            FocusSession.actual_minutes >= rewards.FOCUS_MIN_MINUTES,
        )
    )
    total_xp = sum(xp.values())
    best_day = max(series, key=lambda r: r["xp"]) if total_xp else None
    return {
        "days": days,
        "series": series,
        "totals": {
            "xp": total_xp,
            "quests_completed": len(completed),
            "focus_minutes": sum(focus.values()),
            "focus_sessions": int(sessions or 0),
            "active_days": sum(1 for r in series if r["xp"] > 0),
            "avg_daily_xp": round(total_xp / days),
        },
        "completion_rate": completion_rate,
        "closed_quests": {
            "completed": len(completed),
            "failed": sum(1 for c in closed if c[0] == QuestStatus.FAILED),
            "expired": sum(1 for c in closed if c[0] == QuestStatus.EXPIRED),
        },
        "most_productive_weekday": (
            {"weekday": best_wd, "name": calendar.day_name[best_wd], "avg_xp": round(weekday_avg[best_wd])} if best_wd is not None else None
        ),
        "weekday_avg_xp": [{"weekday": wd, "name": calendar.day_abbr[wd], "avg_xp": round(weekday_avg.get(wd, 0))} for wd in range(7)],
        "best_day": best_day,
        "subjects": subject_rows,
        "top_subject": subject_rows[0]["subject"] if subject_rows else None,
        "weekly": weekly,
    }
