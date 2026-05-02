-- Project 2 Supabase schema for Amzur AI Chat

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null unique,
    full_name text,
    password_hash text,
    google_id text unique,
    avatar_url text,
    auth_provider varchar(50) default 'email',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.profiles add column if not exists password_hash text;
alter table public.profiles add column if not exists google_id text;
alter table public.profiles add column if not exists avatar_url text;
alter table public.profiles add column if not exists auth_provider varchar(50) default 'email';

-- Unique constraint on google_id (nullable – NULLs are not considered duplicates in PG)
do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'uq_profiles_google_id'
    ) then
        execute 'alter table public.profiles add constraint uq_profiles_google_id unique (google_id)';
    end if;
end;
$$;

-- Use profiles as the single source of user data.
drop trigger if exists profiles_sync_to_users on public.profiles;
drop function if exists public.sync_profile_to_users();
do $$
begin
    if to_regclass('public.users') is not null then
        execute 'drop trigger if exists users_set_updated_at on public.users';
        execute 'drop table public.users';
    end if;
end;
$$;

create table if not exists public.chat_threads (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    thread_id uuid not null references public.chat_threads(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    model text,
    created_at timestamptz not null default now()
);

create index if not exists idx_chat_threads_user_id on public.chat_threads(user_id);
create index if not exists idx_chat_messages_thread_id on public.chat_messages(thread_id);
create index if not exists idx_chat_messages_user_id on public.chat_messages(user_id);

-- updated_at trigger helper
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- apply updated_at trigger

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists chat_threads_set_updated_at on public.chat_threads;
create trigger chat_threads_set_updated_at
before update on public.chat_threads
for each row execute function public.set_updated_at();

-- Row level security
alter table public.profiles enable row level security;
alter table public.chat_threads enable row level security;
alter table public.chat_messages enable row level security;

-- profiles policies
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
using (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
on public.profiles for insert
with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles for update
using (auth.uid() = id);

-- chat_threads policies
drop policy if exists "threads_select_own" on public.chat_threads;
create policy "threads_select_own"
on public.chat_threads for select
using (auth.uid() = user_id);

drop policy if exists "threads_insert_own" on public.chat_threads;
create policy "threads_insert_own"
on public.chat_threads for insert
with check (auth.uid() = user_id);

drop policy if exists "threads_update_own" on public.chat_threads;
create policy "threads_update_own"
on public.chat_threads for update
using (auth.uid() = user_id);

drop policy if exists "threads_delete_own" on public.chat_threads;
create policy "threads_delete_own"
on public.chat_threads for delete
using (auth.uid() = user_id);

-- chat_messages policies
drop policy if exists "messages_select_own" on public.chat_messages;
create policy "messages_select_own"
on public.chat_messages for select
using (auth.uid() = user_id);

drop policy if exists "messages_insert_own" on public.chat_messages;
create policy "messages_insert_own"
on public.chat_messages for insert
with check (auth.uid() = user_id);

drop policy if exists "messages_delete_own" on public.chat_messages;
create policy "messages_delete_own"
on public.chat_messages for delete
using (auth.uid() = user_id);
