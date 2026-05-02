import asyncio
import os

import asyncpg
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()
    raw = os.getenv("DATABASE_URL", "")
    dsn = raw.replace("postgresql+asyncpg://", "postgresql://", 1)

    last_error = None
    for i in range(5):
        try:
            conn = await asyncpg.connect(dsn=dsn, ssl="require", timeout=20)
            rows = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
            )
            await conn.close()
            print([r["tablename"] for r in rows])
            return
        except Exception as exc:
            last_error = exc
            print(f"retry {i + 1} failed: {exc}")
            await asyncio.sleep(2)

    raise last_error


if __name__ == "__main__":
    asyncio.run(main())
