from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, Now, Session
from app.db.uow import commit
from app.schemas.focus import FocusCompleteOut, FocusOut, FocusStart
from app.schemas.quests import AchievementBrief, LevelOut, RewardLine
from app.services import focus as focus_service
from app.services import progression

router = APIRouter(prefix="/focus", tags=["focus"])


@router.get("")
async def overview(user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    active = await focus_service.active_for(session, user)
    return {
        "active": FocusOut.model_validate(active).model_dump(mode="json") if active else None,
        "summary": await focus_service.summary(session, user, now),
        "history": [
            FocusOut.model_validate(f).model_dump(mode="json") | {"quest_title": title}
            for f, title in await focus_service.history(session, user)
        ],
        "server_time": now.isoformat(),
    }


@router.post("/sessions", response_model=FocusOut, status_code=201)
async def start(body: FocusStart, user: CurrentUser, session: Session, now: Now) -> FocusOut:
    fs = await focus_service.start(session, user, planned_minutes=body.planned_minutes, quest_id=body.quest_id, now=now)
    await commit(session)
    return FocusOut.model_validate(fs)


@router.post("/sessions/{session_id}/complete", response_model=FocusCompleteOut)
async def complete(session_id: int, user: CurrentUser, session: Session, now: Now) -> FocusCompleteOut:
    result = await focus_service.complete(session, user, session_id, now)
    await commit(session)
    return FocusCompleteOut(
        session=FocusOut.model_validate(result.session),
        xp=result.reward.xp,
        coins=result.reward.coins,
        breakdown=[RewardLine(label=label, xp=xp) for label, xp in result.reward.lines],
        level=LevelOut(**progression.level_payload(user.total_xp)),
        streak=result.streak,
        achievements=[AchievementBrief(code=a.code, name=a.name, icon=a.icon, tier=a.tier) for a in result.achievements],
    )


@router.post("/sessions/{session_id}/cancel", response_model=FocusOut)
async def cancel(session_id: int, user: CurrentUser, session: Session, now: Now) -> FocusOut:
    fs = await focus_service.cancel(session, user, session_id, now)
    await commit(session)
    return FocusOut.model_validate(fs)
