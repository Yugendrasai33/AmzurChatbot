"""Run the Supabase schema migration."""
import asyncio
import asyncpg
import os
import traceback
from pathlib import Path

from dotenv import load_dotenv


def _dsn_from_env() -> str:
    load_dotenv()
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is missing in .env")
    # asyncpg expects postgres/postgresql URI, not sqlalchemy dialect suffix
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


async def migrate():
    dsn = _dsn_from_env()
    sql = Path("supabase_schema.sql").read_text()

    last_error = None
    for attempt in range(1, 6):
        try:
            print(f"Connecting to Supabase... (attempt {attempt}/5)")
            conn = await asyncio.wait_for(
                asyncpg.connect(dsn=dsn, ssl="require", timeout=20, command_timeout=60),
                timeout=25,
            )
            print("Connected. Running schema migration...")
            await conn.execute(sql)
            await conn.close()
            print("Migration SQL executed successfully!")

            # Verify in a fresh connection
            conn2 = await asyncpg.connect(dsn=dsn, ssl="require", timeout=20, command_timeout=60)
            rows = await conn2.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            await conn2.close()
            print("Tables in Supabase:", [r["tablename"] for r in rows])
            return
        except Exception as exc:
            last_error = exc
            print(f"Attempt {attempt} failed: {type(exc).__name__}: {repr(exc)}")
            print(traceback.format_exc())
            if attempt < 5:
                await asyncio.sleep(3)

    raise RuntimeError(
        "Migration failed after 5 attempts. "
        f"Last error type={type(last_error).__name__}, value={repr(last_error)}. "
        "If this is a timeout/WinError 10060, update DATABASE_URL to Supabase pooler URL "
        "(Dashboard -> Connect -> Session pooler, port 6543) and run migration again."
    )


if __name__ == "__main__":
    asyncio.run(migrate())
