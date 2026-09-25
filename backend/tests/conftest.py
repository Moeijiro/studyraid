"""Test harness.

Each test gets a fresh database (a temporary SQLite file, or PostgreSQL when
TEST_DATABASE_URL is set; CI runs both) and a controllable clock. Tests drive
the real FastAPI app in-process. Nothing below the HTTP layer is mocked.
"""

import os
import tempfile
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("WORKER_ENABLED", "false")

import app.models
from app.api.deps import get_now
from app.core.rate_limit import ALL_LIMITERS, register_limiter
from app.db import session as db
from app.db.base import Base
from app.main import app

PASSWORD = "correct-horse-battery"


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def advance(self, **kwargs: float) -> datetime:
        self.now += timedelta(**kwargs)
        return self.now

    def set(self, now: datetime) -> datetime:
        self.now = now
        return now


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def database_url() -> Iterator[str]:
    external = os.environ.get("TEST_DATABASE_URL")
    if external:
        yield external
        return
    with tempfile.TemporaryDirectory() as tmp:
        yield f"sqlite+aiosqlite:///{Path(tmp) / 'test.db'}"


@pytest.fixture
async def database(database_url: str) -> AsyncIterator[None]:
    db.configure(database_url, pooled=False)
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await db.engine.dispose()


_CLOCKS: list[Clock] = []


@pytest.fixture
def clock() -> Iterator[Clock]:
    # A Wednesday at 12:00 UTC: mid-week, so weekly windows have room either side.
    c = Clock(datetime(2026, 3, 11, 12, 0, tzinfo=UTC))
    app.dependency_overrides[get_now] = lambda: c.now
    for limiter in ALL_LIMITERS:
        limiter.reset()
    _CLOCKS.append(c)
    yield c
    _CLOCKS.remove(c)
    app.dependency_overrides.pop(get_now, None)


@pytest.fixture
async def client(database: None, clock: Clock) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers={"X-StudyRaid-Client": "web"}) as c:
        yield c


class Player:
    """A registered user plus a client that sends their access token.

    Tests move the clock by hours or days, so the token is re-issued for the
    current test time on each request (what the frontend's refresh flow does).
    """

    def __init__(self, client: httpx.AsyncClient, data: dict[str, Any], clock: "Clock | None" = None):
        self.client = client
        self.id: int = data["user"]["id"]
        self.username: str = data["user"]["username"]
        self.clock = clock

    @property
    def headers(self) -> dict[str, str]:
        from app.core.security import create_access_token

        now = self.clock.now if self.clock else datetime.now(UTC)
        return {"Authorization": f"Bearer {create_access_token(self.id, now)[0]}"}

    async def get(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.get(url, headers=self.headers, **kw)

    async def post(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.post(url, headers=self.headers, **kw)

    async def patch(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.patch(url, headers=self.headers, **kw)

    async def delete(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.delete(url, headers=self.headers, **kw)

    async def quest(self, **fields: Any) -> dict[str, Any]:
        body = {"title": "Homework", "subject": "Mathematics", "difficulty": "normal", **fields}
        r = await self.post("/api/quests", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    async def complete(self, quest_id: int) -> dict[str, Any]:
        r = await self.post(f"/api/quests/{quest_id}/complete")
        assert r.status_code == 200, r.text
        return r.json()

    async def quick_quest(self, **fields: Any) -> dict[str, Any]:
        """Create and immediately complete a quest; returns the completion payload."""
        q = await self.quest(**fields)
        return await self.complete(q["id"])

    async def me(self) -> dict[str, Any]:
        r = await self.get("/api/me/summary")
        assert r.status_code == 200, r.text
        return r.json()


async def register(client: httpx.AsyncClient, username: str, timezone: str = "UTC") -> Player:
    clock = _CLOCKS[-1] if _CLOCKS else None
    register_limiter.reset()  # tests register many users from one "IP"
    r = await client.post(
        "/api/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "display_name": username.title(),
            "password": PASSWORD,
            "timezone": timezone,
        },
    )
    assert r.status_code == 201, r.text
    client.cookies.clear()  # each Player authenticates by header; cookies are tested explicitly
    return Player(client, r.json(), clock)


@pytest.fixture
async def alice(client: httpx.AsyncClient) -> Player:
    return await register(client, "alice")


@pytest.fixture
async def bob(client: httpx.AsyncClient) -> Player:
    return await register(client, "bob")
