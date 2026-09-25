"""Accounts, logins and refresh-token rotation.

Access tokens are short-lived JWTs held in memory by the client. Refresh tokens
are opaque, stored only as SHA-256 digests, sent in an HttpOnly cookie, and
rotated on every use. If a rotated token is ever presented again, someone is
replaying a stolen token, so the whole token family (that login) is revoked.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, Unauthorized
from app.core.security import create_access_token, digest, hash_password, needs_rehash, new_opaque_token, verify_password
from app.models import RefreshSession, User
from app.repositories import users as user_repo


@dataclass
class IssuedTokens:
    user: User
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


async def register(
    session: AsyncSession, *, email: str, username: str, display_name: str, password: str, timezone: str, now: datetime
) -> User:
    if not get_settings().allow_registration:
        raise Forbidden("Registration is disabled on this instance.")
    if await user_repo.by_email(session, email):
        raise Conflict("An account with this email already exists.", code="email_taken")
    if await user_repo.by_username(session, username):
        raise Conflict("That username is taken.", code="username_taken")
    user = User(
        email=email.lower(),
        username=username.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        timezone=timezone,
        avatar_hue=secrets.randbelow(360),
        created_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    user = await user_repo.by_email(session, email)
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise Unauthorized("Incorrect email or password.", code="invalid_credentials")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


async def _issue(session: AsyncSession, user: User, family_id: str, now: datetime, user_agent: str | None) -> IssuedTokens:
    settings = get_settings()
    refresh = new_opaque_token()
    expires = now + timedelta(days=settings.refresh_token_ttl_days)
    session.add(
        RefreshSession(
            user_id=user.id,
            family_id=family_id,
            token_hash=digest(refresh),
            created_at=now,
            expires_at=expires,
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    access, access_exp = create_access_token(user.id, now)
    return IssuedTokens(user, access, access_exp, refresh, expires)


async def login(session: AsyncSession, email: str, password: str, now: datetime, user_agent: str | None = None) -> IssuedTokens:
    user = await authenticate(session, email, password)
    return await _issue(session, user, secrets.token_hex(16), now, user_agent)


async def start_session(session: AsyncSession, user: User, now: datetime, user_agent: str | None = None) -> IssuedTokens:
    return await _issue(session, user, secrets.token_hex(16), now, user_agent)


async def revoke_family(session: AsyncSession, family_id: str, now: datetime) -> None:
    await session.execute(
        update(RefreshSession).where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now)
    )


async def refresh(session: AsyncSession, token: str, now: datetime, user_agent: str | None = None) -> IssuedTokens:
    """Returns the new tokens, or raises. On token reuse, revokes the family and commits
    that revocation before raising, so the stolen token can't be tried again."""
    row = await session.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest(token)))
    if row is None:
        raise Unauthorized("Session not found.", code="invalid_refresh")
    if row.revoked_at is not None or row.rotated_at is not None:
        await revoke_family(session, row.family_id, now)
        await session.commit()
        raise Unauthorized("Session was revoked. Please sign in again.", code="refresh_reused")
    if row.expires_at <= now:
        raise Unauthorized("Session expired. Please sign in again.", code="refresh_expired")
    user = await session.get(User, row.user_id)
    if user is None:
        raise Unauthorized("Session not found.", code="invalid_refresh")
    row.rotated_at = now
    return await _issue(session, user, row.family_id, now, user_agent)


async def logout(session: AsyncSession, token: str, now: datetime) -> None:
    row = await session.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest(token)))
    if row is not None:
        await revoke_family(session, row.family_id, now)


async def change_password(session: AsyncSession, user: User, current: str, new: str, now: datetime) -> None:
    if not verify_password(current, user.password_hash):
        raise Unauthorized("Current password is incorrect.", code="invalid_credentials")
    user.password_hash = hash_password(new)
    # Every other device has to sign in again.
    await session.execute(
        update(RefreshSession).where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now)
    )
