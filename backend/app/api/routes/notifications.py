from typing import Annotated, Any

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, Now, Session
from app.db.uow import commit
from app.services import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: CurrentUser, session: Session, unread: bool = False, limit: Annotated[int, Query(ge=1, le=100)] = 30
) -> dict[str, Any]:
    items = await notifications.list_for(session, user.id, limit=limit, unread_only=unread)
    return {"items": [notifications.serialize(n) for n in items], "unread": await notifications.unread_count(session, user.id)}


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: int, user: CurrentUser, session: Session, now: Now) -> Response:
    await notifications.mark_read(session, user.id, notification_id, now)
    await commit(session)
    return Response(status_code=204)


@router.post("/read-all", status_code=204)
async def mark_all_read(user: CurrentUser, session: Session, now: Now) -> Response:
    await notifications.mark_all_read(session, user.id, now)
    await commit(session)
    return Response(status_code=204)
