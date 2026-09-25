from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.db import session as db
from app.models import LedgerEntry
from tests.conftest import Clock, Player

pytestmark = pytest.mark.anyio


async def test_xp_reward_is_computed_by_the_server(alice: Player):
    q = await alice.quest(difficulty="hard", estimated_minutes=60)
    assert q["base_xp"] == 75 + 18
    assert q["status"] == "planned"
    r = await alice.post("/api/quests", json={"title": "Cheat", "subject": "Math", "difficulty": "easy", "xp_awarded": 10_000})
    assert r.status_code == 422


async def test_reward_preview_matches_creation(alice: Player):
    preview = (await alice.post("/api/quests/preview-reward", json={"difficulty": "legendary", "estimated_minutes": 120})).json()
    q = await alice.quest(difficulty="legendary", estimated_minutes=120)
    assert preview["base_xp"] == q["base_xp"]


async def test_due_date_must_be_future_and_timezone_aware(alice: Player, clock: Clock):
    past = (clock.now - timedelta(hours=1)).isoformat()
    r = await alice.post("/api/quests", json={"title": "Late", "subject": "Math", "due_at": past})
    assert (r.status_code, r.json()["error"]["code"]) == (400, "invalid_due_date")
    r = await alice.post("/api/quests", json={"title": "Naive", "subject": "Math", "due_at": "2030-01-01T10:00:00"})
    assert r.status_code == 422


async def test_list_filters_and_orders_by_deadline(alice: Player, clock: Clock):
    later = await alice.quest(title="Essay draft", due_at=(clock.now + timedelta(days=3)).isoformat())
    soon = await alice.quest(title="Lab report", subject="Physics", due_at=(clock.now + timedelta(hours=5)).isoformat())
    undated = await alice.quest(title="Read chapter")
    await alice.complete(undated["id"])

    items = (await alice.get("/api/quests", params={"status": ["planned", "active"]})).json()["items"]
    assert [q["id"] for q in items] == [soon["id"], later["id"]]
    assert (await alice.get("/api/quests", params={"subject": "Physics"})).json()["total"] == 1
    assert (await alice.get("/api/quests", params={"search": "essay"})).json()["items"][0]["id"] == later["id"]
    assert (await alice.get("/api/quests", params={"search": "100%_"})).json()["total"] == 0
    assert (await alice.get("/api/quests", params={"status": "completed"})).json()["items"][0]["id"] == undated["id"]


async def test_editing_recomputes_base_xp_and_closed_quests_are_frozen(alice: Player):
    q = await alice.quest(difficulty="easy")
    r = await alice.patch(f"/api/quests/{q['id']}", json={"difficulty": "hard", "estimated_minutes": 100})
    assert r.json()["base_xp"] == 75 + 30
    await alice.complete(q["id"])
    r = await alice.patch(f"/api/quests/{q['id']}", json={"title": "Changed"})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "quest_closed")


async def test_lifecycle_transitions(alice: Player):
    q = await alice.quest()
    assert (await alice.post(f"/api/quests/{q['id']}/start")).json()["status"] == "active"
    assert (await alice.post(f"/api/quests/{q['id']}/start")).status_code == 409
    assert (await alice.post(f"/api/quests/{q['id']}/abandon")).json()["status"] == "failed"
    assert (await alice.post(f"/api/quests/{q['id']}/complete")).status_code == 409


async def test_completion_pays_once_and_totals_match_the_ledger(alice: Player):
    q = await alice.quest(difficulty="normal", estimated_minutes=30)
    done = await alice.complete(q["id"])
    assert done["xp"] == 49  # 40 + 9 effort, no streak yet
    assert done["quest"]["status"] == "completed" and done["quest"]["xp_awarded"] == 49
    assert {"label": "Base", "xp": 49} in done["breakdown"]
    again = await alice.post(f"/api/quests/{q['id']}/complete")
    assert again.status_code == 409

    summary = await alice.me()
    async with db.SessionLocal() as s:
        ledger_xp = await s.scalar(select(func.sum(LedgerEntry.xp)).where(LedgerEntry.user_id == alice.id))
    assert summary["level"]["total_xp"] == ledger_xp  # includes First Blood's achievement XP
    assert ledger_xp == 49 + 25


async def test_level_up_sends_a_notification(alice: Player):
    for _ in range(2):
        await alice.quick_quest(difficulty="legendary", estimated_minutes=240)
    summary = await alice.me()
    assert summary["level"]["level"] >= 2
    notes = (await alice.get("/api/notifications")).json()["items"]
    assert any(n["kind"] == "level_up" and n["title"] == "You reached Level 2" for n in notes)


async def test_late_completion_inside_grace_is_halved_and_after_grace_is_refused(alice: Player, clock: Clock):
    late = await alice.quest(due_at=(clock.now + timedelta(hours=1)).isoformat())
    gone = await alice.quest(due_at=(clock.now + timedelta(hours=1)).isoformat())
    clock.advance(hours=3)
    done = await alice.complete(late["id"])
    assert done["xp"] == 20 and any(line["label"] == "Late" for line in done["breakdown"])
    clock.advance(hours=24)
    r = await alice.post(f"/api/quests/{gone['id']}/complete")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "quest_expired")


async def test_completed_quests_cannot_be_deleted(alice: Player):
    open_q = await alice.quest()
    done_q = await alice.quest()
    await alice.complete(done_q["id"])
    assert (await alice.delete(f"/api/quests/{open_q['id']}")).status_code == 204
    assert (await alice.get(f"/api/quests/{open_q['id']}")).status_code == 404
    assert (await alice.delete(f"/api/quests/{done_q['id']}")).status_code == 409


async def test_farming_hits_the_daily_soft_cap(alice: Player):
    xps = [(await alice.quick_quest(difficulty="legendary", estimated_minutes=240))["xp"] for _ in range(5)]
    assert xps[0] == 222
    assert xps[-1] < 100  # past 600 quest XP in a day, extra XP counts at 25%


async def test_history_lists_most_recently_closed_first(alice: Player, clock: Clock):
    first = await alice.quick_quest(title="First")
    clock.advance(hours=1)
    second = await alice.quick_quest(title="Second")
    items = (await alice.get("/api/quests", params={"status": ["completed", "failed"]})).json()["items"]
    assert [q["id"] for q in items] == [second["quest"]["id"], first["quest"]["id"]]
