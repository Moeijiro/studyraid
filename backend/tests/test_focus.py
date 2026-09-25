import pytest

from tests.conftest import Clock, Player

pytestmark = pytest.mark.anyio


async def start(p: Player, minutes: int = 25, **extra: object) -> dict:
    r = await p.post("/api/focus/sessions", json={"planned_minutes": minutes, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def test_session_cannot_be_completed_before_the_time_is_up(alice: Player, clock: Clock):
    fs = await start(alice, 25)
    clock.advance(minutes=10)
    r = await alice.post(f"/api/focus/sessions/{fs['id']}/complete")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "focus_not_finished"
    assert r.json()["error"]["details"]["remaining_seconds"] == 15 * 60


async def test_completed_session_pays_half_an_xp_per_minute(alice: Player, clock: Clock):
    fs = await start(alice, 50)
    clock.advance(minutes=50, seconds=3)
    r = await alice.post(f"/api/focus/sessions/{fs['id']}/complete")
    body = r.json()
    assert r.status_code == 200 and body["xp"] == 25 and body["session"]["actual_minutes"] == 50
    assert body["streak"] == 1
    summary = (await alice.get("/api/focus")).json()["summary"]
    assert (summary["today_sessions"], summary["today_minutes"]) == (1, 50)


async def test_credit_is_capped_at_the_planned_length(alice: Player, clock: Clock):
    fs = await start(alice, 25)
    clock.advance(hours=5)
    body = (await alice.post(f"/api/focus/sessions/{fs['id']}/complete")).json()
    assert body["session"]["actual_minutes"] == 25 and body["xp"] == 12


async def test_only_one_session_at_a_time_but_stale_ones_are_closed(alice: Player, clock: Clock):
    await start(alice, 25)
    r = await alice.post("/api/focus/sessions", json={"planned_minutes": 25})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "focus_active")
    clock.advance(hours=2)  # 25 minutes planned + an hour of grace have passed
    fresh = await start(alice, 25)
    history = (await alice.get("/api/focus")).json()["history"]
    assert history[0]["status"] == "cancelled"
    assert fresh["status"] == "active"


async def test_cancelled_and_short_sessions_earn_nothing(alice: Player, clock: Clock):
    fs = await start(alice, 30)
    clock.advance(minutes=12)
    assert (await alice.post(f"/api/focus/sessions/{fs['id']}/cancel")).json()["status"] == "cancelled"
    short = await start(alice, 5)
    clock.advance(minutes=5)
    body = (await alice.post(f"/api/focus/sessions/{short['id']}/complete")).json()
    assert body["xp"] == 0 and body["streak"] == 0  # under 10 minutes doesn't count for the streak
    assert (await alice.me())["level"]["total_xp"] == 0


async def test_daily_focus_xp_cap(alice: Player, clock: Clock):
    total = 0
    for _ in range(3):
        fs = await start(alice, 90)
        clock.advance(minutes=90, seconds=1)
        total += (await alice.post(f"/api/focus/sessions/{fs['id']}/complete")).json()["xp"]
        clock.advance(minutes=1)
    assert total == 120  # 240 rewarded minutes per day


async def test_duration_limits(alice: Player):
    assert (await alice.post("/api/focus/sessions", json={"planned_minutes": 2})).status_code == 422
    assert (await alice.post("/api/focus/sessions", json={"planned_minutes": 500})).status_code == 422


async def test_focus_can_target_an_open_quest_only(alice: Player, clock: Clock):
    q = await alice.quest()
    fs = await start(alice, 25, quest_id=q["id"])
    assert fs["quest_id"] == q["id"]
    clock.advance(minutes=26)
    await alice.post(f"/api/focus/sessions/{fs['id']}/complete")
    await alice.complete(q["id"])
    r = await alice.post("/api/focus/sessions", json={"planned_minutes": 25, "quest_id": q["id"]})
    assert r.status_code == 409


async def test_sessions_finish_within_tolerance(alice: Player, clock: Clock):
    fs = await start(alice, 25)
    clock.advance(minutes=24, seconds=45)  # tab timers drift; 15 s early is accepted
    assert (await alice.post(f"/api/focus/sessions/{fs['id']}/complete")).status_code == 200
