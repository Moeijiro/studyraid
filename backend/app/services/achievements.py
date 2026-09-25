"""Builds activity stats from the database and unlocks achievements."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_date, local_hour
from app.db.uow import emit
from app.engine import rewards
from app.engine.achievements import (
    ACHIEVEMENTS,
    BY_CODE,
    AchievementDef,
    ActivityStats,
    is_early_bird_hour,
    is_night_owl_hour,
    newly_unlocked,
)
from app.engine.progression import level_for_xp
from app.engine.rewards import Difficulty
from app.models import (
    FocusSession,
    FocusStatus,
    LedgerEntry,
    LedgerSource,
    PartyMember,
    Quest,
    QuestStatus,
    User,
    UserAchievement,
)
from app.services import notifications, progression


async def build_stats(session: AsyncSession, user: User, now: datetime) -> ActivityStats:
    completed = (
        await session.execute(
            select(Quest.difficulty, Quest.subject, Quest.closed_at, Quest.due_at).where(
                Quest.user_id == user.id, Quest.status == QuestStatus.COMPLETED
            )
        )
    ).all()
    hours = [local_hour(closed, user.timezone) for _, _, closed, _ in completed if closed]
    early = sum(1 for _, _, closed, due in completed if closed and due and due - closed >= rewards.EARLY_THRESHOLD)

    focus = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(FocusSession.actual_minutes), 0),
                func.coalesce(func.max(FocusSession.actual_minutes), 0),
            ).where(
                FocusSession.user_id == user.id,
                FocusSession.status == FocusStatus.COMPLETED,
                FocusSession.actual_minutes >= rewards.FOCUS_MIN_MINUTES,
            )
        )
    ).one()

    parties = await session.scalar(select(func.count()).select_from(PartyMember).where(PartyMember.user_id == user.id))
    challenges = await session.scalar(
        select(func.count()).select_from(LedgerEntry).where(LedgerEntry.user_id == user.id, LedgerEntry.source == LedgerSource.CHALLENGE)
    )
    streak = await progression.streak_for(session, user, local_date(now, user.timezone))

    return ActivityStats(
        quests_completed=len(completed),
        legendary_completed=sum(1 for d, *_ in completed if d == Difficulty.LEGENDARY),
        early_completions=early,
        night_owl_completions=sum(1 for h in hours if is_night_owl_hour(h)),
        early_bird_completions=sum(1 for h in hours if is_early_bird_hour(h)),
        subjects_completed=len({s.strip().lower() for _, s, *_ in completed}),
        focus_sessions=int(focus[0]),
        focus_minutes=int(focus[1]),
        longest_focus_minutes=int(focus[2]),
        longest_streak=streak.longest,
        level=level_for_xp(user.total_xp),
        parties_joined=int(parties or 0),
        challenges_completed=int(challenges or 0),
    )


def serialize(defn: AchievementDef, stats: ActivityStats | None, unlocked_at: datetime | None) -> dict[str, Any]:
    value = defn.value(stats) if stats else 0
    return {
        "code": defn.code,
        "name": defn.name,
        "description": defn.description,
        "icon": defn.icon,
        "tier": defn.tier,
        "xp": rewards.ACHIEVEMENT_XP[defn.tier],
        "target": defn.target,
        "progress": min(value, defn.target),
        "unlocked_at": unlocked_at.isoformat() if unlocked_at else None,
    }


async def unlocked(session: AsyncSession, user_id: int) -> dict[str, datetime]:
    rows = await session.execute(select(UserAchievement.code, UserAchievement.unlocked_at).where(UserAchievement.user_id == user_id))
    return {code: at for code, at in rows.all()}


async def check(session: AsyncSession, user: User, now: datetime) -> list[AchievementDef]:
    """Unlock everything the user now qualifies for.

    Achievement XP can itself cross a level threshold ("Double Digits"), so this
    repeats until nothing new unlocks. It's bounded by the number of definitions.
    """
    gained: list[AchievementDef] = []
    for _ in range(len(ACHIEVEMENTS)):
        stats = await build_stats(session, user, now)
        owned = await unlocked(session, user.id)
        new = newly_unlocked(stats, owned)
        if not new:
            break
        for defn in new:
            try:
                async with session.begin_nested():
                    session.add(UserAchievement(user_id=user.id, code=defn.code, unlocked_at=now))
            except IntegrityError:
                continue
            xp = rewards.ACHIEVEMENT_XP[defn.tier]
            await progression.award(
                session,
                user,
                source=LedgerSource.ACHIEVEMENT,
                ref=f"achievement:{defn.code}",
                xp=xp,
                coins=rewards.coins_for(xp),
                now=now,
                detail={"code": defn.code, "name": defn.name},
            )
            emit(session, user.id, "achievement", achievement=serialize(defn, stats, now))
            await notifications.notify(
                session,
                user.id,
                kind="achievement",
                title=f"Achievement unlocked: {defn.name}",
                body=f"{defn.description} +{xp} XP",
                link="/achievements",
                dedupe_key=f"achievement:{defn.code}",
                now=now,
            )
            gained.append(defn)
    return gained


async def list_all(session: AsyncSession, user: User, now: datetime) -> list[dict[str, Any]]:
    stats = await build_stats(session, user, now)
    owned = await unlocked(session, user.id)
    return [serialize(d, stats, owned.get(d.code)) for d in ACHIEVEMENTS]


async def recent(session: AsyncSession, user: User, limit: int = 4) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(UserAchievement.code, UserAchievement.unlocked_at)
        .where(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.unlocked_at.desc(), UserAchievement.id.desc())
        .limit(limit)
    )
    return [serialize(BY_CODE[c], None, at) | {"progress": BY_CODE[c].target} for c, at in rows.all() if c in BY_CODE]
