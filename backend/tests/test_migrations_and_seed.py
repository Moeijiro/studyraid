import asyncio
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import func, select

from alembic import command
from app.db import session as db
from app.db.base import Base
from app.db.session import make_engine

BACKEND = Path(__file__).resolve().parents[1]


def test_migrations_match_the_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`alembic upgrade head` must produce exactly the schema the models declare."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.chdir(BACKEND)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")

    async def diff() -> list:
        engine = make_engine(url)
        async with engine.connect() as conn:
            result = await conn.run_sync(
                lambda c: compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
            )
        await engine.dispose()
        return result

    assert asyncio.run(diff()) == []


@pytest.mark.anyio
async def test_demo_seed_runs_through_the_real_services(database: None):
    """A short demo world: everything in it must have come out of the services."""
    from app.models import LedgerEntry, Party, PartyChallenge, User, UserAchievement
    from app.seed.demo import build

    summary = await build(days=21)
    async with db.SessionLocal() as s:
        maks = await s.scalar(select(User).where(User.username == "maks"))
        assert maks is not None and maks.total_xp == summary["maks_xp"]
        ledger_total = await s.scalar(select(func.sum(LedgerEntry.xp)).where(LedgerEntry.user_id == maks.id))
        assert maks.total_xp == ledger_total  # cached total == ledger
        assert await s.scalar(select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == maks.id)) >= 5
        assert await s.scalar(select(func.count()).select_from(Party)) == 2
        assert await s.scalar(select(func.count()).select_from(PartyChallenge)) >= 2
