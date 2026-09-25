from datetime import UTC, datetime, timedelta

import pytest

from app.workers import scheduler
from tests.conftest import Clock, Player, register

pytestmark = pytest.mark.anyio


async def test_streak_grows_across_days_and_breaks_after_a_gap(alice: Player, clock: Clock):
    for _ in range(3):
        await alice.quick_quest()
        clock.advance(days=1)
    s = (await alice.me())["streak"]
    assert (s["current"], s["at_risk"]) == (3, True)  # day 4 not done yet
    clock.advance(days=1)
    s = (await alice.me())["streak"]
    assert (s["current"], s["longest"]) == (0, 3)


async def test_streak_days_follow_the_users_time_zone(client, clock: Clock):
    kyiv = await register(client, "kyiv", timezone="Europe/Kyiv")  # UTC+2 in March
    clock.set(datetime(2026, 3, 10, 21, 30, tzinfo=UTC))  # 23:30 on the 10th in Kyiv
    await kyiv.quick_quest()
    clock.set(datetime(2026, 3, 10, 22, 30, tzinfo=UTC))  # 00:30 on the 11th in Kyiv, same UTC day
    await kyiv.quick_quest()
    assert (await kyiv.me())["streak"]["current"] == 2
    days = {d["date"]: d for d in (await kyiv.get("/api/me/heatmap")).json()["days"]}
    assert days["2026-03-10"]["active"] and days["2026-03-11"]["active"]


async def test_streak_bonus_applies_on_later_days(alice: Player, clock: Clock):
    first = await alice.quick_quest(difficulty="easy")
    clock.advance(days=1)
    second = await alice.quick_quest(difficulty="easy")
    assert first["xp"] == 20
    assert second["xp"] == 20 + round(20 * 0.02)
    assert second["streak"] == 2


async def test_streak_milestone_notification(alice: Player, clock: Clock):
    for _ in range(3):
        await alice.quick_quest()
        clock.advance(days=1)
    titles = [n["title"] for n in (await alice.get("/api/notifications")).json()["items"]]
    assert "🔥 Your 3-day streak is active" in titles


async def test_streak_freeze_is_bought_with_coins_and_covers_a_missed_day(alice: Player, clock: Clock):
    r = await alice.post("/api/me/streak-freeze")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "insufficient_coins")
    for _ in range(4):  # earn coins and build a streak
        for _ in range(3):
            await alice.quick_quest(difficulty="legendary", estimated_minutes=240)
        clock.advance(days=1)
    coins_before = (await alice.me())["coins"]
    r = await alice.post("/api/me/streak-freeze")
    assert r.status_code == 200 and r.json()["coins"] == coins_before - 150
    # Day 5 is skipped entirely. The scheduler on day 6 spends the freeze.
    clock.advance(days=1, hours=1)
    await scheduler.run_once(clock.now)
    me = await alice.me()
    assert me["streak"]["freezes"] == 0 and me["streak"]["current"] == 4
    heat = {d["date"]: d for d in (await alice.get("/api/me/heatmap")).json()["days"]}
    assert heat[(clock.now - timedelta(days=1)).date().isoformat()]["frozen"]


async def test_first_blood_unlocks_once_and_pays_achievement_xp(alice: Player):
    done = await alice.quick_quest()
    assert [a["code"] for a in done["achievements"]] == ["first_blood"]
    again = await alice.quick_quest()
    assert again["achievements"] == []
    items = {a["code"]: a for a in (await alice.get("/api/me/achievements")).json()}
    assert items["first_blood"]["unlocked_at"] is not None
    assert items["adventurer"]["progress"] == 2 and items["adventurer"]["target"] == 10
    notes = [n["title"] for n in (await alice.get("/api/notifications")).json()["items"]]
    assert notes.count("Achievement unlocked: First Blood") == 1


async def test_boss_slayer_and_night_owl_come_from_real_activity(client, clock: Clock):
    owl = await register(client, "owl", timezone="Europe/Kyiv")
    clock.set(datetime(2026, 3, 11, 21, 40, tzinfo=UTC))  # 23:40 in Kyiv
    done = await owl.quick_quest(difficulty="legendary")
    codes = {a["code"] for a in done["achievements"]}
    assert {"boss_slayer", "night_owl", "first_blood"} <= codes


async def test_locked_in_after_five_focus_sessions(alice: Player, clock: Clock):
    unlocked = []
    for _ in range(5):
        fs = (await alice.post("/api/focus/sessions", json={"planned_minutes": 25})).json()
        clock.advance(minutes=26)
        unlocked += [a["code"] for a in (await alice.post(f"/api/focus/sessions/{fs['id']}/complete")).json()["achievements"]]
    assert "locked_in" in unlocked


async def test_polymath_counts_distinct_subjects(alice: Player):
    for subject in ["Math", "Physics", "Chemistry", "History"]:
        await alice.quick_quest(subject=subject)
    items = {a["code"]: a for a in (await alice.get("/api/me/achievements")).json()}
    assert items["polymath"]["unlocked_at"] is None and items["polymath"]["progress"] == 4
    done = await alice.quick_quest(subject="physics ")  # same subject, different spelling
    assert "polymath" not in [a["code"] for a in done["achievements"]]
    done = await alice.quick_quest(subject="Biology")
    assert "polymath" in [a["code"] for a in done["achievements"]]
