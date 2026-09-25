"""Study parties: membership, invites and the party's XP picture."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.db.uow import emit
from app.models import (
    ChallengeStatus,
    FocusSession,
    FocusStatus,
    InviteStatus,
    LedgerEntry,
    LedgerSource,
    Party,
    PartyChallenge,
    PartyInvite,
    PartyMember,
    PartyRole,
    Quest,
    QuestStatus,
    User,
)
from app.repositories import parties as party_repo
from app.repositories import users as user_repo
from app.services import achievements, challenges, notifications

MAX_MEMBERS = 8
MAX_PARTIES_PER_USER = 5
PARTY_ICONS = ("sword", "shield", "flame", "moon", "star", "crown", "book", "rocket", "atom", "leaf", "zap", "compass")
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def _invite_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


def party_week_start(now: datetime) -> datetime:
    """Parties mix time zones, so party weeks run Monday 00:00 to Monday 00:00 UTC."""
    day = now.astimezone(UTC).date()
    monday = day - timedelta(days=day.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)


async def get_for_member(session: AsyncSession, user: User, party_id: int) -> tuple[Party, PartyMember]:
    """Non-members get 404, not 403: a party's existence isn't revealed to outsiders."""
    party = await session.get(Party, party_id)
    member = await party_repo.membership(session, party_id, user.id) if party else None
    if party is None or member is None:
        raise NotFound("Party not found.")
    return party, member


def _require_owner(member: PartyMember) -> None:
    if member.role != PartyRole.OWNER:
        raise Forbidden("Only the party leader can do that.")


async def _check_capacity(session: AsyncSession, party: Party) -> None:
    if await party_repo.member_count(session, party.id) >= MAX_MEMBERS:
        raise Conflict(f"Parties are limited to {MAX_MEMBERS} members.", code="party_full")


async def _check_user_limit(session: AsyncSession, user: User) -> None:
    if len(await party_repo.party_ids_of(session, user.id)) >= MAX_PARTIES_PER_USER:
        raise Conflict(f"You can be in at most {MAX_PARTIES_PER_USER} parties.", code="too_many_parties")


async def _add_member(session: AsyncSession, party: Party, user: User, role: PartyRole, now: datetime) -> PartyMember:
    member = PartyMember(party_id=party.id, user_id=user.id, role=role, joined_at=now)
    session.add(member)
    await session.flush()
    for m in await party_repo.members(session, party.id):
        emit(session, m.user_id, "party_member_joined", party_id=party.id, user_id=user.id, display_name=user.display_name)
    await achievements.check(session, user, now)
    return member


async def create(session: AsyncSession, user: User, *, name: str, description: str, icon: str, hue: int, now: datetime) -> Party:
    if icon not in PARTY_ICONS:
        raise AppError("Unknown party icon.", code="invalid_icon")
    await _check_user_limit(session, user)
    party = Party(name=name, description=description, icon=icon, hue=hue, owner_id=user.id, invite_code=_invite_code(), created_at=now)
    session.add(party)
    await session.flush()
    await _add_member(session, party, user, PartyRole.OWNER, now)
    return party


async def update(session: AsyncSession, user: User, party_id: int, changes: dict[str, Any]) -> Party:
    party, member = await get_for_member(session, user, party_id)
    _require_owner(member)
    if "icon" in changes and changes["icon"] not in PARTY_ICONS:
        raise AppError("Unknown party icon.", code="invalid_icon")
    for k, v in changes.items():
        setattr(party, k, v)
    return party


async def rotate_invite_code(session: AsyncSession, user: User, party_id: int) -> Party:
    party, member = await get_for_member(session, user, party_id)
    _require_owner(member)
    party.invite_code = _invite_code()
    return party


async def invite(session: AsyncSession, user: User, party_id: int, username: str, now: datetime) -> PartyInvite:
    party, _ = await get_for_member(session, user, party_id)
    invitee = await user_repo.by_username(session, username)
    if invitee is None:
        raise NotFound("No user with that username.")
    if invitee.id == user.id:
        raise AppError("You're already in this party.", code="invalid_invite")
    if await party_repo.membership(session, party.id, invitee.id):
        raise Conflict("That user is already a member.")
    pending = await session.scalar(
        select(PartyInvite).where(
            PartyInvite.party_id == party.id, PartyInvite.invitee_id == invitee.id, PartyInvite.status == InviteStatus.PENDING
        )
    )
    if pending is not None:
        raise Conflict("That user already has a pending invite.")
    await _check_capacity(session, party)
    inv = PartyInvite(party_id=party.id, inviter_id=user.id, invitee_id=invitee.id, status=InviteStatus.PENDING, created_at=now)
    session.add(inv)
    await session.flush()
    await notifications.notify(
        session,
        invitee.id,
        kind="party_invite",
        title=f"{user.display_name} invited you to {party.name}",
        body="Open your parties to accept or decline.",
        link="/party",
        dedupe_key=f"invite:{inv.id}",
        now=now,
    )
    emit(session, invitee.id, "party_invite", invite_id=inv.id)
    return inv


async def respond(session: AsyncSession, user: User, invite_id: int, accept: bool, now: datetime) -> PartyInvite:
    inv = await session.scalar(select(PartyInvite).where(PartyInvite.id == invite_id, PartyInvite.invitee_id == user.id))
    if inv is None:
        raise NotFound("Invite not found.")
    if inv.status != InviteStatus.PENDING:
        raise Conflict("This invite was already answered.")
    inv.responded_at = now
    if not accept:
        inv.status = InviteStatus.DECLINED
        return inv
    party = await session.get(Party, inv.party_id)
    if party is None:
        raise NotFound("Party not found.")
    await _check_capacity(session, party)
    await _check_user_limit(session, user)
    inv.status = InviteStatus.ACCEPTED
    await _add_member(session, party, user, PartyRole.MEMBER, now)
    return inv


async def join_by_code(session: AsyncSession, user: User, code: str, now: datetime) -> Party:
    party = await session.scalar(select(Party).where(Party.invite_code == code.strip().upper()))
    if party is None:
        raise NotFound("That invite code doesn't match a party.")
    if await party_repo.membership(session, party.id, user.id):
        raise Conflict("You're already in this party.")
    await _check_capacity(session, party)
    await _check_user_limit(session, user)
    await _add_member(session, party, user, PartyRole.MEMBER, now)
    return party


async def leave(session: AsyncSession, user: User, party_id: int) -> None:
    party, member = await get_for_member(session, user, party_id)
    members = await party_repo.members(session, party.id)
    if len(members) == 1:
        await session.delete(party)  # last one out disbands the party
        return
    if member.role == PartyRole.OWNER:
        # Leadership passes to the longest-standing member.
        successor = next(m for m in members if m.user_id != user.id)
        successor.role = PartyRole.OWNER
        party.owner_id = successor.user_id
    await session.delete(member)
    for m in members:
        emit(session, m.user_id, "party_member_left", party_id=party.id, user_id=user.id)


async def remove_member(session: AsyncSession, user: User, party_id: int, target_user_id: int) -> None:
    party, member = await get_for_member(session, user, party_id)
    _require_owner(member)
    if target_user_id == user.id:
        raise AppError("Use leave to remove yourself.", code="invalid_target")
    target = await party_repo.membership(session, party.id, target_user_id)
    if target is None:
        raise NotFound("That user isn't in this party.")
    await session.delete(target)


async def delete(session: AsyncSession, user: User, party_id: int) -> None:
    party, member = await get_for_member(session, user, party_id)
    _require_owner(member)
    await session.delete(party)


async def pending_invites(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(PartyInvite, Party, User)
            .join(Party, Party.id == PartyInvite.party_id)
            .join(User, User.id == PartyInvite.inviter_id)
            .where(PartyInvite.invitee_id == user.id, PartyInvite.status == InviteStatus.PENDING)
            .order_by(PartyInvite.created_at.desc())
        )
    ).all()
    return [
        {
            "id": inv.id,
            "party": {"id": p.id, "name": p.name, "icon": p.icon, "hue": p.hue},
            "from": inviter.display_name,
            "created_at": inv.created_at.isoformat(),
        }
        for inv, p, inviter in rows
    ]


# --- Party XP picture -------------------------------------------------------------


async def _member_stats(session: AsyncSession, members: list[PartyMember], since: datetime | None) -> dict[int, dict[str, int]]:
    """XP, quests and focus minutes per member, counting only time spent in the party."""
    out: dict[int, dict[str, int]] = {}
    for m in members:
        start = max(m.joined_at, since) if since else m.joined_at
        xp = await session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.xp), 0)).where(
                LedgerEntry.user_id == m.user_id, LedgerEntry.created_at >= start, LedgerEntry.source != LedgerSource.SHOP
            )
        )
        quests = await session.scalar(
            select(func.count())
            .select_from(Quest)
            .where(Quest.user_id == m.user_id, Quest.status == QuestStatus.COMPLETED, Quest.closed_at >= start)
        )
        focus = await session.scalar(
            select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
                FocusSession.user_id == m.user_id, FocusSession.status == FocusStatus.COMPLETED, FocusSession.ended_at >= start
            )
        )
        out[m.user_id] = {"xp": int(xp or 0), "quests": int(quests or 0), "focus_minutes": int(focus or 0)}
    return out


def summary(party: Party, member_count: int, role: PartyRole | None = None) -> dict[str, Any]:
    return {
        "id": party.id,
        "name": party.name,
        "description": party.description,
        "icon": party.icon,
        "hue": party.hue,
        "member_count": member_count,
        "role": role.value if role else None,
    }


async def detail(session: AsyncSession, user: User, party_id: int, now: datetime) -> dict[str, Any]:
    party, me = await get_for_member(session, user, party_id)
    members = await party_repo.members(session, party.id)
    users = await user_repo.many(session, {m.user_id for m in members})
    week = await _member_stats(session, members, party_week_start(now))
    total = await _member_stats(session, members, None)

    member_rows = []
    for m in members:
        u = users[m.user_id]
        member_rows.append(
            {
                "user_id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "avatar_hue": u.avatar_hue,
                "role": m.role.value,
                "joined_at": m.joined_at.isoformat(),
                "weekly_xp": week[u.id]["xp"],
                "weekly_quests": week[u.id]["quests"],
                "weekly_focus_minutes": week[u.id]["focus_minutes"],
                "total_xp": total[u.id]["xp"],
            }
        )
    member_rows.sort(key=lambda r: -r["weekly_xp"])
    weekly_xp = sum(r["weekly_xp"] for r in member_rows)
    for r in member_rows:
        r["weekly_share"] = round(r["weekly_xp"] / weekly_xp, 4) if weekly_xp else 0.0

    active = await party_repo.active_challenges(session, [party.id])
    past = list(
        await session.scalars(
            select(PartyChallenge)
            .where(PartyChallenge.party_id == party.id, PartyChallenge.status != ChallengeStatus.ACTIVE)
            .order_by(PartyChallenge.ends_at.desc())
            .limit(5)
        )
    )
    return {
        **summary(party, len(members), me.role),
        "invite_code": party.invite_code if me.role == PartyRole.OWNER else None,
        "party_xp": sum(r["total_xp"] for r in member_rows),
        "weekly_xp": weekly_xp,
        "week_starts_at": party_week_start(now).isoformat(),
        "members": member_rows,
        "challenges": [await challenges.serialize(session, c, now, members) for c in active],
        "past_challenges": [await challenges.serialize(session, c, now, members) for c in past],
        "activity": await activity_feed(session, members, users),
    }


async def activity_feed(session: AsyncSession, members: list[PartyMember], users: dict[int, User], limit: int = 15) -> list[dict[str, Any]]:
    """Recent member activity. Shows subject and difficulty, not quest titles or descriptions."""
    if not members:
        return []
    joined = {m.user_id: m.joined_at for m in members}
    rows = list(
        await session.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.user_id.in_(joined),
                LedgerEntry.source.in_([LedgerSource.QUEST, LedgerSource.FOCUS, LedgerSource.ACHIEVEMENT, LedgerSource.CHALLENGE]),
            )
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .limit(limit * 3)
        )
    )
    feed = []
    for e in rows:
        if e.created_at < joined[e.user_id]:
            continue
        u = users[e.user_id]
        d = e.detail or {}
        if e.source == LedgerSource.QUEST:
            difficulty = str(d.get("difficulty", ""))
            article = "an" if difficulty[:1] in ("e", "a", "i", "o", "u") else "a"
            text = f"completed {article} {difficulty} {d.get('subject', '')} quest"
        elif e.source == LedgerSource.FOCUS:
            text = f"focused for {d.get('minutes', 0)} minutes"
        elif e.source == LedgerSource.ACHIEVEMENT:
            text = f"unlocked {d.get('name', 'an achievement')}"
        else:
            text = f"cleared the challenge {d.get('title', '')}".strip()
        feed.append(
            {
                "id": e.id,
                "user_id": u.id,
                "display_name": u.display_name,
                "avatar_hue": u.avatar_hue,
                "kind": e.source.value,
                "text": text,
                "xp": e.xp,
                "at": e.created_at.isoformat(),
            }
        )
        if len(feed) >= limit:
            break
    return feed


async def list_mine(session: AsyncSession, user: User, now: datetime) -> list[dict[str, Any]]:
    out = []
    for party in await party_repo.parties_of(session, user.id):
        members = await party_repo.members(session, party.id)
        me = next(m for m in members if m.user_id == user.id)
        week = await _member_stats(session, members, party_week_start(now))
        active = await party_repo.active_challenges(session, [party.id])
        out.append(
            {
                **summary(party, len(members), me.role),
                "weekly_xp": sum(s["xp"] for s in week.values()),
                "active_challenge": await challenges.serialize(session, active[0], now, members) if active else None,
            }
        )
    return out
