from datetime import timedelta

import pytest

from app.services.analytics import heat_level
from tests.conftest import Clock, Player

pytestmark = pytest.mark.anyio


async def test_overview_aggregates_real_activity(alice: Player, clock: Clock):
    # Monday: two physics quests. Tuesday: one math quest and a focus session.
    clock.set(clock.now - timedelta(days=2))  # Monday 9 March
    p1 = await alice.quick_quest(subject="Physics", difficulty="hard")
    p2 = await alice.quick_quest(subject="Physics")
    clock.advance(days=1)
    m1 = await alice.quick_quest(subject="Math")
    fs = (await alice.post("/api/focus/sessions", json={"planned_minutes": 50})).json()
    clock.advance(minutes=50, seconds=2)
    await alice.post(f"/api/focus/sessions/{fs['id']}/complete")
    abandoned = await alice.quest(subject="History")
    await alice.post(f"/api/quests/{abandoned['id']}/abandon")
    clock.advance(days=1)

    o = (await alice.get("/api/analytics/overview", params={"days": 7})).json()
    series = {d["date"]: d for d in o["series"]}
    assert len(o["series"]) == 7
    assert series["2026-03-09"]["quests"] == 2 and series["2026-03-10"]["focus_minutes"] == 50
    assert o["totals"]["quests_completed"] == 3
    assert o["totals"]["xp"] == sum(d["xp"] for d in o["series"])
    assert o["completion_rate"] == pytest.approx(3 / 4)
    assert o["closed_quests"] == {"completed": 3, "failed": 1, "expired": 0}
    assert o["top_subject"] == "Physics"
    physics = next(s for s in o["subjects"] if s["subject"] == "Physics")
    assert physics["quests"] == 2 and physics["xp"] == p1["xp"] + p2["xp"]
    assert o["most_productive_weekday"]["name"] == "Monday"
    assert m1["xp"] > 0


async def test_empty_account_has_sane_defaults(alice: Player):
    o = (await alice.get("/api/analytics/overview")).json()
    assert o["completion_rate"] is None and o["most_productive_weekday"] is None and o["top_subject"] is None
    assert o["totals"]["xp"] == 0 and len(o["weekly"]) == 8


async def test_heatmap_covers_whole_weeks(alice: Player, clock: Clock):
    await alice.quick_quest(difficulty="legendary", estimated_minutes=240)
    await alice.quick_quest(difficulty="hard", estimated_minutes=60)
    h = (await alice.get("/api/me/heatmap", params={"weeks": 4})).json()
    assert len(h["days"]) == 3 * 7 + 3  # three full weeks + Mon..Wed of this week
    today = h["days"][-1]
    assert today["date"] == "2026-03-11" and today["level"] == 4 and today["active"]


def test_heat_levels():
    assert [heat_level(x) for x in (0, 1, 59, 60, 149, 150, 299, 300, 5000)] == [0, 1, 1, 2, 2, 3, 3, 4, 4]


async def test_leaderboards_are_scoped_and_respect_opt_out(client, alice: Player, bob: Player, clock: Clock):
    from tests.conftest import register

    stranger = await register(client, "stranger")
    party = (await alice.post("/api/parties", json={"name": "Duo", "icon": "star"})).json()
    await bob.post("/api/parties/join", json={"code": party["invite_code"]})
    clock.advance(minutes=1)
    await bob.quick_quest(difficulty="hard")
    await alice.quick_quest(difficulty="easy")
    await stranger.quick_quest(difficulty="legendary")

    board = (await alice.get("/api/leaderboards", params={"scope": "friends", "metric": "xp"})).json()
    assert [r["username"] for r in board["rows"]] == ["bob", "alice"]
    assert board["rows"][0]["rank"] == 1 and board["rows"][1]["is_me"]

    await bob.patch("/api/me", json={"show_on_leaderboards": False})
    board = (await alice.get("/api/leaderboards", params={"scope": str(party["id"]), "metric": "quests"})).json()
    assert [r["username"] for r in board["rows"]] == ["alice"]
    own = (await bob.get("/api/leaderboards", params={"scope": "friends"})).json()
    assert any(r["is_me"] for r in own["rows"])  # opted-out users still see themselves
    assert (await alice.get("/api/leaderboards", params={"scope": "global"})).status_code == 400
