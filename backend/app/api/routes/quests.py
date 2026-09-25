from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select

from app.api.deps import CurrentUser, Now, Session, limit_writes
from app.db.uow import commit
from app.engine import rewards
from app.models import Quest, QuestStatus
from app.repositories import quests as quest_repo
from app.schemas.quests import (
    AchievementBrief,
    CompletionOut,
    LevelOut,
    QuestCreate,
    QuestOut,
    QuestPage,
    QuestUpdate,
    RewardLine,
    RewardPreviewIn,
)
from app.services import progression
from app.services import quests as quest_service

router = APIRouter(prefix="/quests", tags=["quests"])


@router.get("", response_model=QuestPage)
async def list_quests(
    user: CurrentUser,
    session: Session,
    status: Annotated[list[QuestStatus] | None, Query()] = None,
    subject: Annotated[str | None, Query(max_length=40)] = None,
    search: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QuestPage:
    query = quest_repo.list_query(user.id, statuses=status, subject=subject, search=search)
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = await session.scalars(query.limit(limit).offset(offset))
    return QuestPage(items=[QuestOut.model_validate(q) for q in items], total=int(total or 0))


@router.get("/subjects", response_model=list[str])
async def subjects(user: CurrentUser, session: Session) -> list[str]:
    rows = await session.scalars(
        select(Quest.subject).where(Quest.user_id == user.id).group_by(Quest.subject).order_by(func.count().desc())
    )
    return list(rows)


@router.post("/preview-reward")
async def preview_reward(body: RewardPreviewIn, user: CurrentUser) -> dict[str, int]:
    """The base XP a quest would be created with. Bonuses are applied on completion."""
    xp = rewards.base_quest_xp(body.difficulty, body.estimated_minutes)
    return {"base_xp": xp, "coins": rewards.coins_for(xp)}


@router.post("", response_model=QuestOut, status_code=201, dependencies=[Depends(limit_writes)])
async def create_quest(body: QuestCreate, user: CurrentUser, session: Session, now: Now) -> QuestOut:
    quest = await quest_service.create(session, user, quest_service.QuestInput(**body.model_dump()), now)
    await commit(session)
    return QuestOut.model_validate(quest)


@router.get("/{quest_id}", response_model=QuestOut)
async def get_quest(quest_id: int, user: CurrentUser, session: Session) -> QuestOut:
    return QuestOut.model_validate(await quest_service.get(session, user, quest_id))


@router.patch("/{quest_id}", response_model=QuestOut)
async def update_quest(quest_id: int, body: QuestUpdate, user: CurrentUser, session: Session, now: Now) -> QuestOut:
    quest = await quest_service.get(session, user, quest_id)
    await quest_service.update(session, quest, body.model_dump(exclude_unset=True), now)
    await commit(session)
    return QuestOut.model_validate(quest)


@router.delete("/{quest_id}", status_code=204)
async def delete_quest(quest_id: int, user: CurrentUser, session: Session) -> Response:
    quest = await quest_service.get(session, user, quest_id)
    await quest_service.delete(session, quest)
    await commit(session)
    return Response(status_code=204)


@router.post("/{quest_id}/start", response_model=QuestOut)
async def start_quest(quest_id: int, user: CurrentUser, session: Session, now: Now) -> QuestOut:
    quest = await quest_service.start(session, await quest_service.get(session, user, quest_id), now)
    await commit(session)
    return QuestOut.model_validate(quest)


@router.post("/{quest_id}/abandon", response_model=QuestOut)
async def abandon_quest(quest_id: int, user: CurrentUser, session: Session, now: Now) -> QuestOut:
    quest = await quest_service.abandon(session, await quest_service.get(session, user, quest_id), now)
    await commit(session)
    return QuestOut.model_validate(quest)


@router.post("/{quest_id}/complete", response_model=CompletionOut)
async def complete_quest(quest_id: int, user: CurrentUser, session: Session, now: Now) -> CompletionOut:
    quest = await quest_service.get(session, user, quest_id)
    result = await quest_service.complete(session, user, quest, now)
    await commit(session)
    return CompletionOut(
        quest=QuestOut.model_validate(result.quest),
        xp=result.reward.xp,
        coins=result.reward.coins,
        breakdown=[RewardLine(label=label, xp=xp) for label, xp in result.reward.lines],
        level_before=result.level_before,
        level=LevelOut(**progression.level_payload(user.total_xp)),
        streak=result.streak,
        achievements=[AchievementBrief(code=a.code, name=a.name, icon=a.icon, tier=a.tier) for a in result.achievements],
    )
