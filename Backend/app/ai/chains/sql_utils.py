from __future__ import annotations

from app.core.config import settings


def _build_sync_db_url() -> str:
    """Convert the async DATABASE_URL (asyncpg) to a synchronous psycopg2 URL.

    LangChain's SQLDatabase uses SQLAlchemy's synchronous reflection path,
    which requires the psycopg2 driver instead of asyncpg.
    """
    url = settings.DATABASE_URL
    if url is None:
        raise RuntimeError(
            "DATABASE_URL is not set. Cannot build synchronous DB connection."
        )
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
