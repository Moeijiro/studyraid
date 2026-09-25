from typing import Annotated

from pydantic import Field, StringConstraints

from app.models import ChallengeMetric
from app.schemas.common import Input

PartyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]


class PartyCreate(Input):
    name: PartyName
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    icon: str = "sword"
    hue: int = Field(default=265, ge=0, le=359)


class PartyUpdate(Input):
    name: PartyName | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    icon: str | None = None
    hue: int | None = Field(default=None, ge=0, le=359)


class InviteIn(Input):
    username: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{3,24}$")]


class JoinIn(Input):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=16)]


class ChallengeCreate(Input):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=80)]
    metric: ChallengeMetric
    target: int = Field(ge=1, le=100_000)
    duration_days: int = Field(default=7, ge=1, le=14)
