import os
import time

import psycopg2
from dotenv import load_dotenv


SQL = """
create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text,
    email text not null unique,
    password_hash text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_users_email on public.users(email);

alter table public.users enable row level security;

drop policy if exists "users_select_own" on public.users;
create policy "users_select_own"
on public.users for select
using (auth.uid() = id);

drop policy if exists "users_insert_own" on public.users;
create policy "users_insert_own"
on public.users for insert
with check (auth.uid() = id);

drop policy if exists "users_update_own" on public.users;
create policy "users_update_own"
on public.users for update
using (auth.uid() = id);
"""


def main() -> None:
    load_dotenv()
    dsn = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)
    if not dsn:
        raise RuntimeError("DATABASE_URL missing")

    last_error = None
    for i in range(1, 6):
        try:
            print(f"connect attempt {i}/5")
            conn = psycopg2.connect(dsn, connect_timeout=20, sslmode="require")
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(SQL)
            conn.close()
            print("users table migration done")
            return
        except Exception as exc:
            last_error = exc
            print(f"failed attempt {i}: {type(exc).__name__}: {repr(exc)}")
            time.sleep(3)

    raise RuntimeError(f"users table migration failed after retries: {repr(last_error)}")


if __name__ == "__main__":
    main()
