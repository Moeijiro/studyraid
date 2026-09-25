"""Leaderboards among people you study with, never global.

A board covers one party, or all your party-mates at once ("friends"). Users who
opt out of leaderboards are left off other people's boards. You always see
your own row.
"""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import FocusSession, FocusStatus, LedgerEntry, LedgerSource, Quest, QuestStatus, User
from app.repositories import parties as party_repo
from app.repositories import users as user_repo
from app.services.parties import get_for_member, party_week_start

Metric = Literal["xp", "quests", "focus"]


async def _values(session: AsyncSession, ids: list[int], metric: Metric, since: datetime) -> dict[int, int]:
    if metric == "xp":
        q = (
            select(LedgerEntry.user_id, func.coalesce(func.sum(LedgerEntry.xp), 0))
            .where(LedgerEntry.user_id.in_(ids), LedgerEntry.created_at >= since, LedgerEntry.source != LedgerSource.SHOP)
            .group_by(LedgerEntry.user_id)
        )
    elif metric == "quests":
        q = (
            select(Quest.user_id, func.count())
            .where(Quest.user_id.in_(ids), Quest.status == QuestStatus.COMPLETED, Quest.closed_at >= since)
            .group_by(Quest.user_id)
        )
    else:
        q = (
            select(FocusSession.user_id, func.coalesce(func.sum(FocusSession.actual_minutes), 0))
            .where(FocusSession.user_id.in_(ids), FocusSession.status == FocusStatus.COMPLETED, FocusSession.ended_at >= since)
            .group_by(FocusSession.user_id)
        )
    return {uid: int(v) for uid, v in (await session.execute(q)).all()}


async def board(session: AsyncSession, user: User, *, scope: str, metric: Metric, now: datetime) -> dict[str, Any]:
    if scope == "friends":
        ids = await party_repo.mate_ids(session, user.id)
    elif scope.isdigit():
        party, _ = await get_for_member(session, user, int(scope))
        ids = {m.user_id for m in await party_repo.members(session, party.id)}
    else:
        raise AppError("scope must be 'friends' or a party id.", code="invalid_scope")
    users = await user_repo.many(session, ids)
    visible = [u for u in users.values() if u.show_on_leaderboards or u.id == user.id]
    since = party_week_start(now)
    values = await _values(session, [u.id for u in visible], metric, since)
    rows = sorted(
        (
            {
                "user_id": u.id,
                "display_name": u.display_name,
                "username": u.username,
                "avatar_hue": u.avatar_hue,
                "value": values.get(u.id, 0),
                "is_me": u.id == user.id,
            }
            for u in visible
        ),
        key=lambda r: (-int(r["value"]), str(r["display_name"])),
    )
    rank = 0
    last: int | None = None
    for i, r in enumerate(rows, start=1):
        if r["value"] != last:
            rank, last = i, int(r["value"])
        r["rank"] = rank
    return {"scope": scope, "metric": metric, "since": since.isoformat(), "rows": rows}
