import pytest

from tests.conftest import Clock, Player, register

pytestmark = pytest.mark.anyio


async def make_party(owner: Player, name: str = "Night Library") -> dict:
    r = await owner.post("/api/parties", json={"name": name, "icon": "moon", "hue": 265})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_party_makes_the_creator_leader(alice: Player):
    party = await make_party(alice)
    assert party["role"] == "owner" and party["member_count"] == 1
    assert len(party["invite_code"]) == 8
    assert (await alice.post("/api/parties", json={"name": "Bad", "icon": "not-an-icon"})).status_code == 400


async def test_invite_by_username_notifies_and_accepting_joins(alice: Player, bob: Player):
    party = await make_party(alice)
    assert (await alice.post(f"/api/parties/{party['id']}/invites", json={"username": "ghost_user"})).status_code == 404
    r = await alice.post(f"/api/parties/{party['id']}/invites", json={"username": "bob"})
    assert r.status_code == 201
    assert (await alice.post(f"/api/parties/{party['id']}/invites", json={"username": "bob"})).status_code == 409

    notes = (await bob.get("/api/notifications")).json()["items"]
    assert notes[0]["kind"] == "party_invite"
    invite = (await bob.get("/api/parties")).json()["invites"][0]
    detail = (await bob.post(f"/api/parties/invites/{invite['id']}/accept")).json()
    assert detail["member_count"] == 2 and detail["role"] == "member"
    assert (await bob.post(f"/api/parties/invites/{invite['id']}/accept")).status_code == 409


async def test_declining_an_invite(alice: Player, bob: Player):
    party = await make_party(alice)
    await alice.post(f"/api/parties/{party['id']}/invites", json={"username": "bob"})
    invite = (await bob.get("/api/parties")).json()["invites"][0]
    assert (await bob.post(f"/api/parties/invites/{invite['id']}/decline")).status_code == 204
    assert (await bob.post(f"/api/parties/invites/{invite['id']}/accept")).status_code == 409
    assert (await bob.get("/api/parties")).json()["parties"] == []


async def test_join_by_code_and_party_capacity(client, alice: Player):
    party = await make_party(alice)
    code = party["invite_code"].lower()  # codes are case-insensitive
    for i in range(7):
        p = await register(client, f"member{i}")
        assert (await p.post("/api/parties/join", json={"code": code})).status_code == 200
    late = await register(client, "latecomer")
    r = await late.post("/api/parties/join", json={"code": code})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "party_full")


async def test_rotating_the_code_invalidates_the_old_one(alice: Player, bob: Player):
    party = await make_party(alice)
    new_code = (await alice.post(f"/api/parties/{party['id']}/invite-code")).json()["invite_code"]
    assert (await bob.post("/api/parties/join", json={"code": party["invite_code"]})).status_code == 404
    assert (await bob.post("/api/parties/join", json={"code": new_code})).status_code == 200


async def test_leader_leaving_hands_over_and_last_member_disbands(alice: Player, bob: Player):
    party = await make_party(alice)
    await bob.post("/api/parties/join", json={"code": party["invite_code"]})
    assert (await alice.post(f"/api/parties/{party['id']}/leave")).status_code == 204
    detail = (await bob.get(f"/api/parties/{party['id']}")).json()
    assert detail["role"] == "owner" and detail["member_count"] == 1
    assert (await bob.post(f"/api/parties/{party['id']}/leave")).status_code == 204
    assert (await bob.get(f"/api/parties/{party['id']}")).status_code == 404


async def test_leader_can_remove_members(alice: Player, bob: Player):
    party = await make_party(alice)
    await bob.post("/api/parties/join", json={"code": party["invite_code"]})
    assert (await alice.delete(f"/api/parties/{party['id']}/members/{bob.id}")).status_code == 204
    assert (await bob.get(f"/api/parties/{party['id']}")).status_code == 404


async def test_party_xp_counts_only_time_spent_in_the_party(alice: Player, bob: Player, clock: Clock):
    await bob.quick_quest(difficulty="legendary")  # before joining: not the party's
    party = await make_party(alice)
    clock.advance(minutes=1)
    await bob.post("/api/parties/join", json={"code": party["invite_code"]})
    clock.advance(minutes=1)
    done = await bob.quick_quest(difficulty="normal")
    clock.advance(minutes=1)
    a = await alice.quick_quest(difficulty="hard")

    detail = (await alice.get(f"/api/parties/{party['id']}")).json()
    members = {m["username"]: m for m in detail["members"]}
    party_up = 25  # achievement XP for joining a party counts: it was earned as a member
    assert members["bob"]["weekly_xp"] == done["xp"] + party_up  # the pre-join legendary quest is excluded
    assert members["alice"]["weekly_xp"] == a["xp"] + 25 + party_up  # quest + First Blood + Party Up
    assert detail["weekly_xp"] == members["bob"]["weekly_xp"] + members["alice"]["weekly_xp"]
    assert sum(m["weekly_share"] for m in detail["members"]) == pytest.approx(1.0, abs=0.001)
    kinds = [e["kind"] for e in detail["activity"]]
    assert "quest" in kinds
    assert all("Homework" not in e["text"] for e in detail["activity"])  # titles stay private


async def test_party_up_achievement(alice: Player):
    await make_party(alice)
    items = {a["code"]: a for a in (await alice.get("/api/me/achievements")).json()}
    assert items["party_up"]["unlocked_at"] is not None


async def test_a_user_can_be_in_at_most_five_parties(alice: Player):
    for i in range(5):
        await make_party(alice, f"Party {i}")
    r = await alice.post("/api/parties", json={"name": "Sixth", "icon": "star"})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "too_many_parties")
