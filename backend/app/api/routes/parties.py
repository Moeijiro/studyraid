from typing import Any

from fastapi import APIRouter, Depends, Response

from app.api.deps import CurrentUser, Now, Session, limit_writes
from app.db.uow import commit
from app.schemas.parties import ChallengeCreate, InviteIn, JoinIn, PartyCreate, PartyUpdate
from app.services import challenges
from app.services import parties as party_service

router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("")
async def my_parties(user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    return {
        "parties": await party_service.list_mine(session, user, now),
        "invites": await party_service.pending_invites(session, user),
        "icons": list(party_service.PARTY_ICONS),
    }


@router.post("", status_code=201, dependencies=[Depends(limit_writes)])
async def create_party(body: PartyCreate, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    party = await party_service.create(session, user, **body.model_dump(), now=now)
    await commit(session)
    return await party_service.detail(session, user, party.id, now)


@router.post("/join")
async def join(body: JoinIn, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    party = await party_service.join_by_code(session, user, body.code, now)
    await commit(session)
    return await party_service.detail(session, user, party.id, now)


@router.post("/invites/{invite_id}/accept")
async def accept_invite(invite_id: int, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    inv = await party_service.respond(session, user, invite_id, True, now)
    await commit(session)
    return await party_service.detail(session, user, inv.party_id, now)


@router.post("/invites/{invite_id}/decline", status_code=204)
async def decline_invite(invite_id: int, user: CurrentUser, session: Session, now: Now) -> Response:
    await party_service.respond(session, user, invite_id, False, now)
    await commit(session)
    return Response(status_code=204)


@router.get("/{party_id}")
async def get_party(party_id: int, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    return await party_service.detail(session, user, party_id, now)


@router.patch("/{party_id}")
async def update_party(party_id: int, body: PartyUpdate, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    await party_service.update(session, user, party_id, body.model_dump(exclude_unset=True, exclude_none=True))
    await commit(session)
    return await party_service.detail(session, user, party_id, now)


@router.delete("/{party_id}", status_code=204)
async def delete_party(party_id: int, user: CurrentUser, session: Session) -> Response:
    await party_service.delete(session, user, party_id)
    await commit(session)
    return Response(status_code=204)


@router.post("/{party_id}/invite-code")
async def rotate_code(party_id: int, user: CurrentUser, session: Session) -> dict[str, str]:
    party = await party_service.rotate_invite_code(session, user, party_id)
    await commit(session)
    return {"invite_code": party.invite_code}


@router.post("/{party_id}/invites", status_code=201, dependencies=[Depends(limit_writes)])
async def invite(party_id: int, body: InviteIn, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    inv = await party_service.invite(session, user, party_id, body.username, now)
    await commit(session)
    return {"id": inv.id, "status": inv.status.value}


@router.post("/{party_id}/leave", status_code=204)
async def leave(party_id: int, user: CurrentUser, session: Session) -> Response:
    await party_service.leave(session, user, party_id)
    await commit(session)
    return Response(status_code=204)


@router.delete("/{party_id}/members/{user_id}", status_code=204)
async def remove_member(party_id: int, user_id: int, user: CurrentUser, session: Session) -> Response:
    await party_service.remove_member(session, user, party_id, user_id)
    await commit(session)
    return Response(status_code=204)


@router.post("/{party_id}/challenges", status_code=201, dependencies=[Depends(limit_writes)])
async def create_challenge(party_id: int, body: ChallengeCreate, user: CurrentUser, session: Session, now: Now) -> dict[str, Any]:
    party, _ = await party_service.get_for_member(session, user, party_id)
    ch = await challenges.create(
        session, user, party, title=body.title, metric=body.metric, target=body.target, duration_days=body.duration_days, now=now
    )
    await commit(session)
    return await challenges.serialize(session, ch, now)
