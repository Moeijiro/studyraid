from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Now, Session
from app.services import analytics
from app.services import leaderboards as leaderboard_service

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview")
async def overview(user: CurrentUser, session: Session, now: Now, days: Annotated[int, Query(ge=7, le=90)] = 30) -> dict[str, Any]:
    return await analytics.overview(session, user, now, days)


@router.get("/leaderboards")
async def leaderboards(
    user: CurrentUser,
    session: Session,
    now: Now,
    scope: Annotated[str, Query(max_length=12)] = "friends",
    metric: Literal["xp", "quests", "focus"] = "xp",
) -> dict[str, Any]:
    return await leaderboard_service.board(session, user, scope=scope, metric=metric, now=now)
