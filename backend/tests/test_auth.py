import httpx
import pytest

from tests.conftest import PASSWORD, Clock, Player, register

pytestmark = pytest.mark.anyio


async def test_register_returns_token_and_sets_httponly_refresh_cookie(client: httpx.AsyncClient):
    r = await client.post(
        "/api/auth/register",
        json={"email": "Maks@Example.com", "username": "Maks_1", "display_name": "Maks", "password": PASSWORD, "timezone": "Europe/Kyiv"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["user"]["email"] == "maks@example.com"
    assert body["user"]["username"] == "maks_1"
    assert "password" not in r.text and "password_hash" not in r.text
    cookie = r.headers["set-cookie"]
    assert "sr_refresh=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie


async def test_duplicate_email_and_username_are_rejected(client: httpx.AsyncClient, alice: Player):
    base = {"display_name": "X", "password": PASSWORD}
    r = await client.post("/api/auth/register", json={**base, "email": "ALICE@example.com", "username": "someone"})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "email_taken")
    r = await client.post("/api/auth/register", json={**base, "email": "new@example.com", "username": "Alice"})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "username_taken")


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"password": "short"}, "password"),
        ({"password": "aaaaaaaaaaaa"}, "password"),
        ({"username": "no spaces!"}, "username"),
        ({"email": "not-an-email"}, "email"),
        ({"timezone": "Mars/Olympus"}, "timezone"),
    ],
)
async def test_registration_validation_uses_the_error_envelope(client: httpx.AsyncClient, patch: dict[str, str], field: str):
    body = {"email": "v@example.com", "username": "valid", "display_name": "V", "password": PASSWORD, **patch}
    r = await client.post("/api/auth/register", json=body)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert any(d["field"] == field for d in err["details"])


async def test_login_does_not_reveal_whether_an_account_exists(client: httpx.AsyncClient, alice: Player):
    wrong = await client.post("/api/auth/login", json={"email": "alice@example.com", "password": "nope-nope-nope"})
    unknown = await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    ok = await client.post("/api/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD})
    assert ok.status_code == 200


async def test_protected_routes_need_a_valid_unexpired_token(client: httpx.AsyncClient, clock: Clock):
    r = await client.post(
        "/api/auth/register", json={"email": "t@example.com", "username": "tokens", "display_name": "T", "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get("/api/me")).status_code == 401
    assert (await client.get("/api/me", headers={"Authorization": "Bearer garbage"})).status_code == 401
    assert (await client.get("/api/me", headers=headers)).status_code == 200
    clock.advance(minutes=16)
    r = await client.get("/api/me", headers=headers)
    assert (r.status_code, r.json()["error"]["code"]) == (401, "token_expired")


async def test_tokens_signed_with_another_key_are_rejected(client: httpx.AsyncClient, alice: Player, clock: Clock):
    import jwt

    forged = jwt.encode(
        {"sub": str(alice.id), "exp": int(clock.now.timestamp()) + 600, "iss": "studyraid", "typ": "access"}, "x" * 40, algorithm="HS256"
    )
    assert (await client.get("/api/me", headers={"Authorization": f"Bearer {forged}"})).status_code == 401


async def test_refresh_rotates_and_detects_reuse(client: httpx.AsyncClient):
    r = await client.post(
        "/api/auth/register", json={"email": "r@example.com", "username": "rotator", "display_name": "R", "password": PASSWORD}
    )
    first = client.cookies.get("sr_refresh")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    second = client.cookies.get("sr_refresh")
    assert second and second != first

    # Replaying the rotated token revokes the whole login, including the new token.
    client.cookies.set("sr_refresh", first)
    r = await client.post("/api/auth/refresh")
    assert (r.status_code, r.json()["error"]["code"]) == (401, "refresh_reused")
    client.cookies.set("sr_refresh", second)
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_refresh_requires_the_client_header(client: httpx.AsyncClient):
    await client.post("/api/auth/register", json={"email": "c@example.com", "username": "csrf", "display_name": "C", "password": PASSWORD})
    r = await client.post("/api/auth/refresh", headers={"X-StudyRaid-Client": ""})
    assert (r.status_code, r.json()["error"]["code"]) == (403, "csrf")


async def test_refresh_token_expires(client: httpx.AsyncClient, clock: Clock):
    await client.post(
        "/api/auth/register", json={"email": "e@example.com", "username": "expiry", "display_name": "E", "password": PASSWORD}
    )
    clock.advance(days=31)
    r = await client.post("/api/auth/refresh")
    assert (r.status_code, r.json()["error"]["code"]) == (401, "refresh_expired")


async def test_logout_revokes_the_refresh_token(client: httpx.AsyncClient):
    await client.post(
        "/api/auth/register", json={"email": "l@example.com", "username": "leaver", "display_name": "L", "password": PASSWORD}
    )
    token = client.cookies.get("sr_refresh")
    assert (await client.post("/api/auth/logout")).status_code == 204
    client.cookies.set("sr_refresh", token)
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_login_is_rate_limited(client: httpx.AsyncClient, alice: Player):
    for _ in range(10):
        await client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"})
    r = await client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


async def test_password_change_signs_out_other_sessions(client: httpx.AsyncClient):
    await client.post(
        "/api/auth/register", json={"email": "p@example.com", "username": "changer", "display_name": "P", "password": PASSWORD}
    )
    old_cookie = client.cookies.get("sr_refresh")
    login = await client.post("/api/auth/login", json={"email": "p@example.com", "password": PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = await client.post("/api/me/password", headers=headers, json={"current_password": "wrong", "new_password": "a-new-strong-pass"})
    assert r.status_code == 401
    r = await client.post("/api/me/password", headers=headers, json={"current_password": PASSWORD, "new_password": "a-new-strong-pass"})
    assert r.status_code == 204
    client.cookies.set("sr_refresh", old_cookie)
    assert (await client.post("/api/auth/refresh")).status_code == 401
    assert (await client.post("/api/auth/login", json={"email": "p@example.com", "password": "a-new-strong-pass"})).status_code == 200


async def test_registration_can_be_disabled(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "allow_registration", False)
    r = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "username": "closed", "display_name": "X", "password": PASSWORD}
    )
    assert r.status_code == 403


async def test_profile_update_validates_timezone(alice: Player):
    assert (await alice.patch("/api/me", json={"timezone": "Nowhere/City"})).status_code == 422
    r = await alice.patch("/api/me", json={"timezone": "Asia/Tokyo", "display_name": "  Al  "})
    assert r.status_code == 200 and r.json()["timezone"] == "Asia/Tokyo" and r.json()["display_name"] == "Al"


async def test_unknown_fields_are_rejected(alice: Player):
    r = await alice.patch("/api/me", json={"total_xp": 99999})
    assert r.status_code == 422


async def test_new_users_get_distinct_ids(client: httpx.AsyncClient):
    a = await register(client, "one")
    b = await register(client, "two")
    assert a.id != b.id


async def test_refresh_without_a_cookie_is_a_quiet_no_session(client: httpx.AsyncClient):
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 204
