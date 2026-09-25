"""Password hashing, access tokens and opaque refresh tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import Unauthorized

_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters
_ALGORITHM = "HS256"
_ISSUER = "studyraid"

# Verifying against a real hash when the user doesn't exist keeps login timing
# the same for unknown emails, so the endpoint can't be used to enumerate accounts.
_DUMMY_HASH = _hasher.hash("timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return _hasher.verify(hashed or _DUMMY_HASH, password) and hashed is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def create_access_token(user_id: int, now: datetime) -> tuple[str, datetime]:
    settings = get_settings()
    expires = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int(expires.timestamp()), "iss": _ISSUER, "typ": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM), expires


def decode_access_token(token: str, now: datetime) -> int:
    """Expiry is checked against the application clock (the same one that issued
    the token), which keeps it consistent with every other time rule."""
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "sub", "iss"], "verify_exp": False},
        )
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid token.") from exc
    if payload.get("typ") != "access":
        raise Unauthorized("Invalid token.")
    if int(payload["exp"]) <= int(now.timestamp()):
        raise Unauthorized("Session expired.", code="token_expired")
    return int(payload["sub"])


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def digest(token: str) -> str:
    """Refresh tokens and WebSocket tickets are stored only as SHA-256 digests."""
    return hashlib.sha256(token.encode()).hexdigest()
