from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.errors import Forbidden, Unauthorized
from app.core.rate_limit import write_limiter
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

Session = Annotated[AsyncSession, Depends(get_session)]

CLIENT_HEADER = "X-StudyRaid-Client"


def get_now() -> datetime:
    """Overridden in tests to move the clock."""
    return utcnow()


Now = Annotated[datetime, Depends(get_now)]


async def get_current_user(session: Session, now: Now, authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Sign in to continue.")
    user_id = decode_access_token(authorization[7:].strip(), now)
    user = await session.get(User, user_id)
    if user is None:
        raise Unauthorized("Account no longer exists.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_client_header(x_studyraid_client: Annotated[str | None, Header()] = None) -> None:
    """Cookie-authenticated endpoints need a custom header. Cross-site pages can't
    send one without a CORS preflight, which the API never approves, so a
    malicious site can't ride the refresh cookie (CSRF)."""
    if x_studyraid_client != "web":
        raise Forbidden("Missing client header.", code="csrf")


async def limit_writes(user: CurrentUser) -> None:
    write_limiter.hit(f"user:{user.id}")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
