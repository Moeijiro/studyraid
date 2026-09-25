import asyncio

from sqlalchemy.engine import Connection

import app.models  # noqa: F401  (registers every table on Base.metadata)
from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import make_engine

target_metadata = Base.metadata


def _url() -> str:
    return context.config.attributes.get("database_url") or get_settings().database_url


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",  # SQLite needs batch mode for ALTER
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = make_engine(_url())
    async with engine.connect() as conn:
        await conn.run_sync(_configure)
    await engine.dispose()


def run_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _configure(connection)
    else:
        asyncio.run(_run_async())
