"""WebSocket delivery, driven through Starlette's TestClient."""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.rate_limit import ALL_LIMITERS
from app.db import session as db
from app.db.base import Base
from app.main import app
from tests.conftest import PASSWORD

ORIGIN = {"origin": "http://localhost:3000"}


async def _create_schema() -> None:
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await db.engine.dispose()


@pytest.fixture
def tc(tmp_path: Path) -> Iterator[TestClient]:
    db.configure(f"sqlite+aiosqlite:///{tmp_path / 'ws.db'}", pooled=False)
    asyncio.run(_create_schema())
    for limiter in ALL_LIMITERS:
        limiter.reset()
    with TestClient(app) as client:
        yield client


def _login(tc: TestClient, username: str) -> dict[str, str]:
    r = tc.post(
        "/api/auth/register",
        json={"email": f"{username}@example.com", "username": username, "display_name": username, "password": PASSWORD},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ticket(tc: TestClient, headers: dict[str, str]) -> str:
    return tc.post("/api/realtime/ticket", headers=headers).json()["ticket"]


def test_completing_a_quest_pushes_xp_and_achievement_events(tc: TestClient):
    headers = _login(tc, "live")
    quest = tc.post("/api/quests", headers=headers, json={"title": "Essay", "subject": "History"}).json()
    with tc.websocket_connect(f"/api/ws?ticket={_ticket(tc, headers)}", headers=ORIGIN) as ws:
        assert ws.receive_json() == {"type": "hello"}
        tc.post(f"/api/quests/{quest['id']}/complete", headers=headers)
        events: list[dict] = []
        while not events or events[-1]["type"] != "quest_completed":
            events.append(ws.receive_json())
    xp = [e for e in events if e["type"] == "xp"]
    assert [e["amount"] for e in xp] == [40, 25]  # the quest, then First Blood
    assert xp[-1]["level"]["total_xp"] == 65
    assert any(e["type"] == "achievement" and e["achievement"]["code"] == "first_blood" for e in events)
    assert any(e["type"] == "notification" and e["notification"]["kind"] == "achievement" for e in events)


def test_party_members_see_challenge_progress_live(tc: TestClient):
    leader = _login(tc, "leader")
    mate = _login(tc, "mate")
    party = tc.post("/api/parties", headers=leader, json={"name": "Live", "icon": "zap"}).json()
    tc.post("/api/parties/join", headers=mate, json={"code": party["invite_code"]})
    tc.post(f"/api/parties/{party['id']}/challenges", headers=leader, json={"title": "Sprint", "metric": "quests_completed", "target": 5})
    quest = tc.post("/api/quests", headers=mate, json={"title": "Q", "subject": "Math"}).json()
    with tc.websocket_connect(f"/api/ws?ticket={_ticket(tc, leader)}", headers=ORIGIN) as ws:
        ws.receive_json()
        tc.post(f"/api/quests/{quest['id']}/complete", headers=mate)
        activity = ws.receive_json()
        progress = ws.receive_json()
    assert activity == {"type": "party_activity", "user_id": activity["user_id"], "display_name": "mate"}
    assert progress["type"] == "challenge_progress" and progress["progress"] == 1 and progress["target"] == 5


def test_tickets_are_single_use_and_required(tc: TestClient):
    headers = _login(tc, "tick")
    ticket = _ticket(tc, headers)
    with tc.websocket_connect(f"/api/ws?ticket={ticket}", headers=ORIGIN) as ws:
        ws.receive_json()
    for bad in (ticket, "forged", ""):
        with pytest.raises(WebSocketDisconnect) as exc:
            with tc.websocket_connect(f"/api/ws?ticket={bad}", headers=ORIGIN) as ws:
                ws.receive_json()
        assert exc.value.code == 4401


def test_foreign_origins_are_refused(tc: TestClient):
    headers = _login(tc, "origin")
    with pytest.raises(WebSocketDisconnect) as exc:
        with tc.websocket_connect(f"/api/ws?ticket={_ticket(tc, headers)}", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert exc.value.code == 4403


def test_ticket_endpoint_requires_auth(tc: TestClient):
    assert tc.post("/api/realtime/ticket").status_code == 401
