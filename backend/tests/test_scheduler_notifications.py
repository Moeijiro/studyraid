from datetime import timedelta

import pytest

from app.workers import scheduler
from tests.conftest import Clock, Player

pytestmark = pytest.mark.anyio


async def test_overdue_quests_expire_once(alice: Player, clock: Clock):
    q = await alice.quest(title="Lab report", due_at=(clock.now + timedelta(hours=2)).isoformat())
    clock.advance(hours=27)
    await scheduler.run_once(clock.now)
    await scheduler.run_once(clock.now)
    assert (await alice.get(f"/api/quests/{q['id']}")).json()["status"] == "expired"
    titles = [n["title"] for n in (await alice.get("/api/notifications")).json()["items"]]
    assert titles.count("Quest expired: Lab report") == 1


async def test_due_soon_reminder_is_sent_once(alice: Player, clock: Clock):
    await alice.quest(subject="Math", due_at=(clock.now + timedelta(hours=20)).isoformat())
    await alice.quest(subject="Physics", due_at=(clock.now + timedelta(days=3)).isoformat())
    await scheduler.run_once(clock.now)
    clock.advance(hours=1)
    await scheduler.run_once(clock.now)
    notes = (await alice.get("/api/notifications")).json()
    due = [n for n in notes["items"] if n["kind"] == "due_soon"]
    assert [n["title"] for n in due] == ["Your Math quest is due tomorrow"]
    assert notes["unread"] == 1


async def test_streak_at_risk_reminder_in_the_evening(alice: Player, clock: Clock):
    await alice.quick_quest()
    clock.advance(days=1, hours=8)  # next day, 20:00 UTC
    await scheduler.run_once(clock.now)
    titles = [n["title"] for n in (await alice.get("/api/notifications")).json()["items"]]
    assert "🔥 Your 1-day streak ends at midnight" in titles


async def test_mark_read_and_read_all(alice: Player):
    await alice.quick_quest()
    await alice.quick_quest(difficulty="legendary", estimated_minutes=240)
    data = (await alice.get("/api/notifications")).json()
    assert data["unread"] >= 2
    first = data["items"][0]["id"]
    assert (await alice.post(f"/api/notifications/{first}/read")).status_code == 204
    assert (await alice.get("/api/notifications")).json()["unread"] == data["unread"] - 1
    await alice.post("/api/notifications/read-all")
    assert (await alice.get("/api/notifications", params={"unread": True})).json()["items"] == []
