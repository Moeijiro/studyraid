"""Nobody can read or change another user's data. Foreign ids behave exactly like
ids that don't exist (404), so they can't be used to probe."""

import pytest

from tests.conftest import Player

pytestmark = pytest.mark.anyio


async def test_quests_are_private(alice: Player, bob: Player):
    q = await alice.quest()
    for method, url, body in [
        ("get", f"/api/quests/{q['id']}", None),
        ("patch", f"/api/quests/{q['id']}", {"title": "mine now"}),
        ("delete", f"/api/quests/{q['id']}", None),
        ("post", f"/api/quests/{q['id']}/start", None),
        ("post", f"/api/quests/{q['id']}/complete", None),
        ("post", f"/api/quests/{q['id']}/abandon", None),
    ]:
        kwargs = {"json": body} if body else {}
        r = await getattr(bob, method)(url, **kwargs)
        assert r.status_code == 404, (method, url)
    assert (await bob.get("/api/quests")).json()["total"] == 0
    assert (await alice.get(f"/api/quests/{q['id']}")).json()["status"] == "planned"


async def test_focus_sessions_are_private(alice: Player, bob: Player):
    fs = (await alice.post("/api/focus/sessions", json={"planned_minutes": 25})).json()
    assert (await bob.post(f"/api/focus/sessions/{fs['id']}/complete")).status_code == 404
    assert (await bob.post(f"/api/focus/sessions/{fs['id']}/cancel")).status_code == 404
    other = await alice.quest()
    r = await bob.post("/api/focus/sessions", json={"planned_minutes": 25, "quest_id": other["id"]})
    assert r.status_code == 404


async def test_notifications_are_private(alice: Player, bob: Player):
    await alice.quick_quest()  # unlocks First Blood -> notification
    note = (await alice.get("/api/notifications")).json()["items"][0]
    assert (await bob.post(f"/api/notifications/{note['id']}/read")).status_code == 404
    assert (await bob.get("/api/notifications")).json()["items"] == []


async def test_parties_are_invisible_to_outsiders(alice: Player, bob: Player):
    party = (await alice.post("/api/parties", json={"name": "Owls", "icon": "moon"})).json()
    pid = party["id"]
    assert (await bob.get(f"/api/parties/{pid}")).status_code == 404
    assert (await bob.patch(f"/api/parties/{pid}", json={"name": "Taken"})).status_code == 404
    assert (await bob.delete(f"/api/parties/{pid}")).status_code == 404
    assert (await bob.post(f"/api/parties/{pid}/invites", json={"username": "bob"})).status_code == 404
    assert (await bob.get("/api/leaderboards", params={"scope": str(pid)})).status_code == 404


async def test_members_cannot_use_leader_powers(client, alice: Player, bob: Player):
    from tests.conftest import register

    carol = await register(client, "carol")
    party = (await alice.post("/api/parties", json={"name": "Owls", "icon": "moon"})).json()
    await bob.post("/api/parties/join", json={"code": party["invite_code"]})
    await carol.post("/api/parties/join", json={"code": party["invite_code"]})
    pid = party["id"]

    member_view = (await bob.get(f"/api/parties/{pid}")).json()
    assert member_view["invite_code"] is None  # only the leader sees the code
    assert (await bob.patch(f"/api/parties/{pid}", json={"name": "Mine"})).status_code == 403
    assert (await bob.delete(f"/api/parties/{pid}/members/{carol.id}")).status_code == 403
    assert (await bob.post(f"/api/parties/{pid}/invite-code")).status_code == 403
    r = await bob.post(f"/api/parties/{pid}/challenges", json={"title": "Go team", "metric": "quests_completed", "target": 10})
    assert r.status_code == 403


async def test_invites_can_only_be_answered_by_the_invitee(client, alice: Player, bob: Player):
    from tests.conftest import register

    carol = await register(client, "carol")
    party = (await alice.post("/api/parties", json={"name": "Owls", "icon": "moon"})).json()
    await alice.post(f"/api/parties/{party['id']}/invites", json={"username": "carol"})
    invite = (await carol.get("/api/parties")).json()["invites"][0]
    assert (await bob.post(f"/api/parties/invites/{invite['id']}/accept")).status_code == 404
    assert (await carol.post(f"/api/parties/invites/{invite['id']}/accept")).status_code == 200
