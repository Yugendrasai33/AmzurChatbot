from urllib.parse import quote, urlparse, urlunparse
from urllib.parse import quote, unquote, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _normalize_database_url(raw_url: str) -> str:
    """Quote password safely when special chars like @ are present, preserve asyncpg driver."""
    parsed = urlparse(raw_url)
    if not parsed.password:
        return raw_url

    # unquote first to avoid double-encoding (e.g. %40 → %2540)
    safe_password = quote(unquote(parsed.password), safe="")
    if parsed.username:
        netloc = f"{parsed.username}:{safe_password}@{parsed.hostname}"
    else:
        netloc = f":{safe_password}@{parsed.hostname}"

    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    # Preserve the scheme (e.g., postgresql+asyncpg, postgresql)
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for Project 2 DB persistence.")

DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

try:
    engine = create_async_engine(DATABASE_URL, future=True, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception as e:
    print(f"Warning: Failed to initialize database engine: {e}")
    engine = None
    SessionLocal = None


async def get_db() -> AsyncSession:
    if SessionLocal is None:
        raise RuntimeError("Database session not initialized. Check DATABASE_URL in .env")
    async with SessionLocal() as session:
        yield session
