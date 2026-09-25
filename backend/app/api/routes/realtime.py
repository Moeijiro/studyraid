"""Live updates over one WebSocket per tab: XP, level-ups, achievements,
notifications and party challenge progress."""

import asyncio
import contextlib
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.realtime.hub import hub
from app.realtime.tickets import TICKET_TTL_SECONDS, tickets

router = APIRouter(tags=["realtime"])

PING_SECONDS = 25


@router.post("/realtime/ticket")
async def issue_ticket(user: CurrentUser) -> dict[str, object]:
    return {"ticket": tickets.issue(user.id), "expires_in": TICKET_TTL_SECONDS}


@router.websocket("/ws")
async def socket(websocket: WebSocket, ticket: Annotated[str, Query(max_length=128)] = "") -> None:
    # Browsers attach Origin to WebSocket handshakes. Checking it stops another
    # site from opening a socket with a ticket it somehow obtained (CSWSH).
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in get_settings().allowed_origins:
        await websocket.close(code=4403)
        return
    user_id = tickets.redeem(ticket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = hub.subscribe(user_id)

    async def pump() -> None:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=PING_SECONDS)
            except TimeoutError:
                event = {"type": "ping"}
            await websocket.send_json(event)

    sender = asyncio.create_task(pump())
    try:
        await websocket.send_json({"type": "hello"})
        while True:  # the client sends nothing meaningful; this detects disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await sender
        hub.unsubscribe(user_id, queue)
