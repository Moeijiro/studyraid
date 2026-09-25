from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChallengeStatus, Party, PartyChallenge, PartyMember


async def membership(session: AsyncSession, party_id: int, user_id: int) -> PartyMember | None:
    return await session.scalar(select(PartyMember).where(PartyMember.party_id == party_id, PartyMember.user_id == user_id))


async def members(session: AsyncSession, party_id: int) -> list[PartyMember]:
    rows = await session.scalars(select(PartyMember).where(PartyMember.party_id == party_id).order_by(PartyMember.joined_at))
    return list(rows)


async def member_count(session: AsyncSession, party_id: int) -> int:
    return int(await session.scalar(select(func.count()).select_from(PartyMember).where(PartyMember.party_id == party_id)) or 0)


async def parties_of(session: AsyncSession, user_id: int) -> list[Party]:
    rows = await session.scalars(
        select(Party)
        .join(PartyMember, PartyMember.party_id == Party.id)
        .where(PartyMember.user_id == user_id)
        .order_by(PartyMember.joined_at)
    )
    return list(rows)


async def party_ids_of(session: AsyncSession, user_id: int) -> list[int]:
    return list(await session.scalars(select(PartyMember.party_id).where(PartyMember.user_id == user_id)))


async def mate_ids(session: AsyncSession, user_id: int) -> set[int]:
    """Everyone who shares at least one party with the user, the user included."""
    party_ids = select(PartyMember.party_id).where(PartyMember.user_id == user_id)
    rows = await session.scalars(select(PartyMember.user_id).where(PartyMember.party_id.in_(party_ids)).distinct())
    return set(rows) | {user_id}


async def active_challenges(session: AsyncSession, party_ids: list[int]) -> list[PartyChallenge]:
    if not party_ids:
        return []
    rows = await session.scalars(
        select(PartyChallenge)
        .where(PartyChallenge.party_id.in_(party_ids), PartyChallenge.status == ChallengeStatus.ACTIVE)
        .order_by(PartyChallenge.ends_at)
    )
    return list(rows)
