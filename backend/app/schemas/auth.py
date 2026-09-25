from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator

from app.core.clock import is_valid_timezone
from app.schemas.common import Input, Schema

Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{3,24}$")]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]


def _check_tz(value: str) -> str:
    if not is_valid_timezone(value):
        raise ValueError("unknown time zone")
    return value


class RegisterIn(Input):
    email: EmailStr
    username: Username
    display_name: DisplayName
    password: Password
    timezone: str = "UTC"

    _tz = field_validator("timezone")(_check_tz)

    @field_validator("password")
    @classmethod
    def _not_trivial(cls, v: str) -> str:
        if len(set(v)) < 4:
            raise ValueError("password is too repetitive")
        return v


class LoginIn(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(Schema):
    id: int
    email: str
    username: str
    display_name: str
    timezone: str
    avatar_hue: int
    show_on_leaderboards: bool
    created_at: datetime


class TokenOut(Schema):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_at: datetime
    user: UserOut


class ProfileUpdate(Input):
    display_name: DisplayName | None = None
    timezone: str | None = None
    avatar_hue: int | None = Field(default=None, ge=0, le=359)
    show_on_leaderboards: bool | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        return _check_tz(v) if v is not None else v


class PasswordChange(Input):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password
