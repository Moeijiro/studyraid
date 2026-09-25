from typing import Annotated, Any

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, Now, Session
from app.db.uow import commit
from app.schemas.auth import PasswordChange, ProfileUpdate, UserOut
from app.schemas.quests import QuestOut
from app.services import achievements, analytics, dashboard, shop
from app.services import auth as auth_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
async def profile(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("", response_model=UserOut)
async def update_profile(body: ProfileUpdate, user: CurrentUser, session: Session) -> UserOut:
    for key, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, key, value)
    await commit(session)
    return UserOut.model_validate(user)


@router.post("/password", status_code=204)
async def change_password(body: PasswordChange, user: CurrentUser, session: Session, now: Now) -> Response:
    await auth_service.change_password(session, user, body.current_password, body.new_password, now)
    await commit(session)
    return Response(status_code=204)


@router.get("/summary")
async def summary(user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    data = await dashboard.summary(session, user, now)
    for key in ("today_quests", "completed_today", "upcoming_quests"):
        data[key] = [QuestOut.model_validate(q).model_dump(mode="json") for q in data[key]]
    data["user"] = UserOut.model_validate(user).model_dump(mode="json")
    return data


@router.get("/achievements")
async def my_achievements(user: CurrentUser, session: Session, now: Now) -> list[dict[str, Any]]:
    return await achievements.list_all(session, user, now)


@router.get("/heatmap")
async def heatmap(user: CurrentUser, session: Session, now: Now, weeks: Annotated[int, Query(ge=4, le=53)] = 26) -> dict[str, Any]:
    return await analytics.heatmap(session, user, now, weeks)


@router.post("/streak-freeze")
async def buy_streak_freeze(user: CurrentUser, session: Session, now: Now) -> dict[str, int]:
    await shop.buy_streak_freeze(session, user, now)
    await commit(session)
    return {"coins": user.coins, "streak_freezes": user.streak_freezes, "price": shop.STREAK_FREEZE_PRICE}
