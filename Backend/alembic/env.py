"""Alembic env.py – async runner for SQLAlchemy 2.0 + asyncpg."""
import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Make the Backend package importable when alembic is run from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import ChatMessage, ChatThread, Profile  # noqa: F401, E402 – register models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use the DATABASE_URL from settings (postgresql+asyncpg://…)
DATABASE_URL: str = settings.DATABASE_URL  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_migrations_sync(connection) -> None:
    """Configure context and run migrations inside a single synchronous call."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        version_table="alembic_version",
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Offline mode – generates SQL without connecting to the DB.
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version",
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode – connects to the DB and applies migrations.
# ---------------------------------------------------------------------------

async def _run_migrations_async() -> None:
    engine: AsyncEngine = create_async_engine(DATABASE_URL, future=True)
    async with engine.connect() as connection:
        # configure + run + begin_transaction must all happen in one run_sync call
        await connection.run_sync(_run_migrations_sync)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_migrations_async())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
