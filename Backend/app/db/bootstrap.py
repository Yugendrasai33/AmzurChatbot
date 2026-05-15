import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base
from app.models import Attachment, ChatMessage, ChatThread, Profile  # noqa: F401

logger = logging.getLogger(__name__)


async def ensure_tables(engine: AsyncEngine) -> None:
    """Create missing tables on startup for local/dev bootstrapping."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to bootstrap database tables: {e}")
        logger.error(
            "Database may not be reachable from this network. "
            "If your DATABASE_URL host is db.<project-ref>.supabase.co and resolves to IPv6 only, "
            "use the Supabase Session/Transaction pooler URL (port 6543) in .env instead."
        )
        # Don't crash - app can still run with in-memory features
        # User should verify DB credentials and restart
