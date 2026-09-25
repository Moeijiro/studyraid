import pytest

from app.workers import scheduler
from tests.conftest import Clock, Player, register

pytestmark = pytest.mark.anyio


async def party_of(owner: Player, *members: Player) -> int:
    party = (await owner.post("/api/parties", json={"name": "Raid", "icon": "sword"})).json()
    for m in members:
        await m.post("/api/parties/join", json={"code": party["invite_code"]})
    return party["id"]


async def challenge(owner: Player, pid: int, **body: object) -> dict:
    r = await owner.post(f"/api/parties/{pid}/challenges", json={"title": "Raid week", "metric": "quests_completed", "target": 3, **body})
    assert r.status_code == 201, r.text
    return r.json()


async def test_progress_is_derived_from_member_activity(alice: Player, bob: Player, clock: Clock):
    pid = await party_of(alice, bob)
    clock.advance(minutes=1)
    ch = await challenge(alice, pid, target=5)
    assert ch["progress"] == 0 and ch["reward_xp"] >= 40
    await alice.quick_quest()
    await bob.quick_quest()
    await bob.quick_quest()
    detail = (await alice.get(f"/api/parties/{pid}")).json()
    running = detail["challenges"][0]
    assert running["progress"] == 3
    assert {c["display_name"]: c["value"] for c in running["contributions"]} == {"Bob": 2, "Alice": 1}


async def test_reaching_the_target_pays_contributors_once(client, alice: Player, bob: Player, clock: Clock):
    carol = await register(client, "carol")
    pid = await party_of(alice, bob, carol)
    clock.advance(minutes=1)
    ch = await challenge(alice, pid, target=3)
    await alice.quick_quest()
    await bob.quick_quest()
    before_carol = (await carol.me())["level"]["total_xp"]
    await bob.quick_quest()  # third quest completes the challenge

    detail = (await alice.get(f"/api/parties/{pid}")).json()
    assert detail["challenges"] == [] and detail["past_challenges"][0]["status"] == "completed"
    assert (await carol.me())["level"]["total_xp"] == before_carol  # contributed nothing, earned nothing
    notes = [n["title"] for n in (await carol.get("/api/notifications")).json()["items"]]
    assert "Your party completed its challenge" in notes

    bob_ach = {a["code"]: a for a in (await bob.get("/api/me/achievements")).json()}
    assert bob_ach["raid_cleared"]["unlocked_at"] is not None
    xp_before = (await bob.me())["level"]["total_xp"]
    extra = await bob.quick_quest()
    assert (await bob.me())["level"]["total_xp"] == xp_before + extra["xp"]  # no second payout
    assert ch["reward_xp"] > 0


async def test_activity_before_joining_does_not_count(alice: Player, bob: Player, clock: Clock):
    pid = await party_of(alice)
    await challenge(alice, pid, target=5)
    clock.advance(minutes=1)
    await bob.quick_quest()
    await bob.quick_quest()
    clock.advance(minutes=1)
    await bob.post("/api/parties/join", json={"code": (await alice.get(f"/api/parties/{pid}")).json()["invite_code"]})
    running = (await alice.get(f"/api/parties/{pid}")).json()["challenges"][0]
    assert running["progress"] == 0


async def test_focus_minutes_challenge(alice: Player, bob: Player, clock: Clock):
    pid = await party_of(alice, bob)
    await challenge(alice, pid, metric="focus_minutes", target=60, title="An hour together")
    for p in (alice, bob):
        fs = (await p.post("/api/focus/sessions", json={"planned_minutes": 25})).json()
        clock.advance(minutes=25, seconds=5)
        await p.post(f"/api/focus/sessions/{fs['id']}/complete")
    running = (await alice.get(f"/api/parties/{pid}")).json()["challenges"][0]
    assert running["progress"] == 50 and running["unit"] == "minutes"


async def test_unfinished_challenge_fails_when_it_ends(alice: Player, bob: Player, clock: Clock):
    pid = await party_of(alice, bob)
    await challenge(alice, pid, target=10, duration_days=2)
    await bob.quick_quest()
    clock.advance(days=2, minutes=1)
    await scheduler.run_once(clock.now)
    await scheduler.run_once(clock.now)  # a second run doesn't notify twice
    past = (await alice.get(f"/api/parties/{pid}")).json()["past_challenges"][0]
    assert past["status"] == "failed" and past["progress"] == 1
    titles = [n["title"] for n in (await bob.get("/api/notifications")).json()["items"]]
    assert titles.count("Challenge ended: Raid week") == 1


async def test_targets_are_bounded_and_active_challenges_limited(alice: Player):
    pid = await party_of(alice)
    r = await alice.post(f"/api/parties/{pid}/challenges", json={"title": "Too easy", "metric": "focus_minutes", "target": 5})
    assert (r.status_code, r.json()["error"]["code"]) == (400, "invalid_target")
    for i in range(3):
        await challenge(alice, pid, title=f"Challenge {i}")
    r = await alice.post(f"/api/parties/{pid}/challenges", json={"title": "Fourth", "metric": "quests_completed", "target": 5})
    assert r.status_code == 409
