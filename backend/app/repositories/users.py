from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(func.lower(User.email) == email.lower()))


async def by_username(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(func.lower(User.username) == username.lower()))


async def many(session: AsyncSession, ids: set[int]) -> dict[int, User]:
    if not ids:
        return {}
    rows = await session.scalars(select(User).where(User.id.in_(ids)))
    return {u.id: u for u in rows}
