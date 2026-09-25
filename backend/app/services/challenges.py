"""Party challenges: shared goals whose progress is derived from members' activity.

Progress is never stored as a counter. It is recomputed from quests, focus
sessions and the ledger inside the challenge window, and only activity after a
member joined the party counts, so joining a party can't import old work.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, Forbidden
from app.db.uow import emit
from app.engine import rewards
from app.models import (
    ChallengeMetric,
    ChallengeStatus,
    FocusSession,
    FocusStatus,
    LedgerEntry,
    LedgerSource,
    Party,
    PartyChallenge,
    PartyMember,
    PartyRole,
    Quest,
    QuestStatus,
    User,
)
from app.repositories import parties as party_repo
from app.repositories import users as user_repo
from app.services import achievements, notifications, progression

MAX_ACTIVE_PER_PARTY = 3
TARGET_BOUNDS = {
    ChallengeMetric.QUESTS_COMPLETED: (3, 500),
    ChallengeMetric.FOCUS_MINUTES: (60, 20_000),
    ChallengeMetric.XP: (200, 100_000),
}
METRIC_UNIT = {ChallengeMetric.QUESTS_COMPLETED: "quests", ChallengeMetric.FOCUS_MINUTES: "minutes", ChallengeMetric.XP: "XP"}


def default_reward(metric: ChallengeMetric, target: int, members: int) -> int:
    """Scales with how much work the goal represents per member, between 40 and 250 XP."""
    per_member = target / max(members, 1)
    effort = {
        ChallengeMetric.QUESTS_COMPLETED: per_member * 12,
        ChallengeMetric.FOCUS_MINUTES: per_member * 0.4,
        ChallengeMetric.XP: per_member * 0.15,
    }[metric]
    return int(min(250, max(40, round(effort / 5) * 5)))


async def _member_value(session: AsyncSession, ch: PartyChallenge, user_id: int, start: datetime, end: datetime) -> int:
    if ch.metric == ChallengeMetric.QUESTS_COMPLETED:
        q = (
            select(func.count())
            .select_from(Quest)
            .where(Quest.user_id == user_id, Quest.status == QuestStatus.COMPLETED, Quest.closed_at >= start, Quest.closed_at <= end)
        )
    elif ch.metric == ChallengeMetric.FOCUS_MINUTES:
        q = select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.actual_minutes >= rewards.FOCUS_MIN_MINUTES,
            FocusSession.ended_at >= start,
            FocusSession.ended_at <= end,
        )
    else:
        q = select(func.coalesce(func.sum(LedgerEntry.xp), 0)).where(
            LedgerEntry.user_id == user_id,
            LedgerEntry.source != LedgerSource.CHALLENGE,
            LedgerEntry.created_at >= start,
            LedgerEntry.created_at <= end,
        )
    return int(await session.scalar(q) or 0)


async def contributions(session: AsyncSession, ch: PartyChallenge, members: list[PartyMember], now: datetime) -> dict[int, int]:
    end = min(ch.completed_at or ch.ends_at, ch.ends_at, now)
    result: dict[int, int] = {}
    for m in members:
        start = max(ch.starts_at, m.joined_at)
        result[m.user_id] = await _member_value(session, ch, m.user_id, start, end) if start <= end else 0
    return result


async def serialize(session: AsyncSession, ch: PartyChallenge, now: datetime, members: list[PartyMember] | None = None) -> dict[str, Any]:
    members = members if members is not None else await party_repo.members(session, ch.party_id)
    contrib = await contributions(session, ch, members, now)
    total = sum(contrib.values())
    users = await user_repo.many(session, set(contrib))
    return {
        "id": ch.id,
        "party_id": ch.party_id,
        "title": ch.title,
        "metric": ch.metric.value,
        "unit": METRIC_UNIT[ch.metric],
        "target": ch.target,
        "progress": total,
        "reward_xp": ch.reward_xp,
        "starts_at": ch.starts_at.isoformat(),
        "ends_at": ch.ends_at.isoformat(),
        "status": ch.status.value,
        "completed_at": ch.completed_at.isoformat() if ch.completed_at else None,
        "contributions": sorted(
            (
                {"user_id": uid, "display_name": users[uid].display_name, "avatar_hue": users[uid].avatar_hue, "value": v}
                for uid, v in contrib.items()
                if uid in users
            ),
            key=lambda c: -int(c["value"]),
        ),
    }


async def create(
    session: AsyncSession,
    user: User,
    party: Party,
    *,
    title: str,
    metric: ChallengeMetric,
    target: int,
    duration_days: int,
    now: datetime,
) -> PartyChallenge:
    member = await party_repo.membership(session, party.id, user.id)
    if member is None or member.role != PartyRole.OWNER:
        raise Forbidden("Only the party leader can start challenges.")
    low, high = TARGET_BOUNDS[metric]
    if not low <= target <= high:
        raise AppError(f"Target for this challenge must be between {low} and {high}.", code="invalid_target")
    active = await party_repo.active_challenges(session, [party.id])
    if len(active) >= MAX_ACTIVE_PER_PARTY:
        raise Conflict(f"A party can run at most {MAX_ACTIVE_PER_PARTY} challenges at once.")
    count = await party_repo.member_count(session, party.id)
    ch = PartyChallenge(
        party_id=party.id,
        created_by=user.id,
        title=title,
        metric=metric,
        target=target,
        reward_xp=default_reward(metric, target, count),
        starts_at=now,
        ends_at=now + timedelta(days=duration_days),
        status=ChallengeStatus.ACTIVE,
    )
    session.add(ch)
    await session.flush()
    for m in await party_repo.members(session, party.id):
        if m.user_id != user.id:
            await notifications.notify(
                session,
                m.user_id,
                kind="challenge",
                title=f"New party challenge: {title}",
                body=f"{party.name} · {target:,} {METRIC_UNIT[metric]} in {duration_days} days · +{ch.reward_xp} XP each",
                link=f"/party/{party.id}",
                now=now,
            )
    return ch


async def on_activity(session: AsyncSession, user: User, now: datetime) -> None:
    """Tell party-mates something happened, recompute the user's running challenges,
    and settle any that reached their target."""
    for mate_id in await party_repo.mate_ids(session, user.id):
        if mate_id != user.id:
            emit(session, mate_id, "party_activity", user_id=user.id, display_name=user.display_name)
    party_ids = await party_repo.party_ids_of(session, user.id)
    for ch in await party_repo.active_challenges(session, party_ids):
        if not ch.starts_at <= now <= ch.ends_at:
            continue
        members = await party_repo.members(session, ch.party_id)
        contrib = await contributions(session, ch, members, now)
        total = sum(contrib.values())
        for m in members:
            emit(
                session,
                m.user_id,
                "challenge_progress",
                challenge_id=ch.id,
                party_id=ch.party_id,
                progress=total,
                target=ch.target,
                by_user_id=user.id,
            )
        if total >= ch.target:
            await _complete(session, ch, members, contrib, now)


async def _complete(session: AsyncSession, ch: PartyChallenge, members: list[PartyMember], contrib: dict[int, int], now: datetime) -> None:
    # Conditional update: if two completions race, only one settles the reward.
    result = await session.execute(
        update(PartyChallenge)
        .where(PartyChallenge.id == ch.id, PartyChallenge.status == ChallengeStatus.ACTIVE)
        .values(status=ChallengeStatus.COMPLETED, completed_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        return
    await session.refresh(ch)
    party = await session.get(Party, ch.party_id)
    users = await user_repo.many(session, {m.user_id for m in members})
    for m in members:
        member_user = users.get(m.user_id)
        if member_user is None:
            continue
        if contrib.get(m.user_id, 0) > 0:
            await progression.award(
                session,
                member_user,
                source=LedgerSource.CHALLENGE,
                ref=f"challenge:{ch.id}",
                xp=ch.reward_xp,
                coins=rewards.coins_for(ch.reward_xp),
                now=now,
                detail={"title": ch.title, "party": party.name if party else ""},
            )
            await achievements.check(session, member_user, now)
        emit(session, m.user_id, "challenge_completed", challenge_id=ch.id, party_id=ch.party_id, title=ch.title)
        await notifications.notify(
            session,
            m.user_id,
            kind="challenge",
            title="Your party completed its challenge",
            body=f"{ch.title} · +{ch.reward_xp} XP for every contributor"
            if contrib.get(m.user_id, 0) > 0
            else f"{ch.title} was completed.",
            link=f"/party/{ch.party_id}",
            dedupe_key=f"challenge_done:{ch.id}",
            now=now,
        )


async def settle_expired(session: AsyncSession, now: datetime) -> int:
    """Scheduler job: challenges past their end that never reached the target fail."""
    rows = list(
        await session.scalars(select(PartyChallenge).where(PartyChallenge.status == ChallengeStatus.ACTIVE, PartyChallenge.ends_at < now))
    )
    for ch in rows:
        members = await party_repo.members(session, ch.party_id)
        contrib = await contributions(session, ch, members, now)
        total = sum(contrib.values())
        if total >= ch.target:  # reached in the final moments; settle as a success
            await _complete(session, ch, members, contrib, ch.ends_at)
            continue
        ch.status = ChallengeStatus.FAILED
        for m in members:
            await notifications.notify(
                session,
                m.user_id,
                kind="challenge",
                title=f"Challenge ended: {ch.title}",
                body=f"Your party reached {total:,} of {ch.target:,} {METRIC_UNIT[ch.metric]}.",
                link=f"/party/{ch.party_id}",
                dedupe_key=f"challenge_failed:{ch.id}",
                now=now,
            )
    return len(rows)
