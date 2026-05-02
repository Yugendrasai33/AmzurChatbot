import asyncio
from dotenv import dotenv_values
import asyncpg

cfg = dotenv_values(".env")

async def check():
    url = cfg["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=20)
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='profiles' "
        "ORDER BY ordinal_position"
    )
    print("Columns in public.profiles:")
    for r in rows:
        print(" ", r["column_name"])
    ver = await conn.fetch("SELECT version_num FROM public.alembic_version")
    print("Alembic versions:", [r["version_num"] for r in ver])
    await conn.close()

asyncio.run(check())
