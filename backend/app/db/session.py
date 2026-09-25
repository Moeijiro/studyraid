from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def make_engine(url: str, echo: bool = False, *, pooled: bool = True) -> AsyncEngine:
    extra = {} if pooled else {"poolclass": NullPool}
    if url.startswith("sqlite"):
        engine = create_async_engine(url, echo=echo, connect_args={"timeout": 30}, **extra)

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(conn, _record):  # type: ignore[no-untyped-def]
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        return engine
    return create_async_engine(url, echo=echo, pool_pre_ping=True, **extra)


_settings = get_settings()
engine: AsyncEngine = make_engine(_settings.database_url, _settings.sql_echo)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def configure(url: str, *, pooled: bool = True) -> None:
    """Point the app at another database (used by the tests)."""
    global engine, SessionLocal
    engine = make_engine(url, pooled=pooled)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
