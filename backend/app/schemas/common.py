from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Input(BaseModel):
    """Request bodies reject unknown fields, so a client can't slip in `xp_awarded` or `user_id`."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must include a time zone offset")
    return dt.astimezone(UTC)


AwareDatetime = Annotated[datetime, AfterValidator(_aware)]
Hue = Annotated[int, "0..359"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
