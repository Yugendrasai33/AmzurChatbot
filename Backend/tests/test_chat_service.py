from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.services.chat_service import delete_thread, rename_thread


@dataclass
class _FakeResult:
    thread: object | None

    def scalar_one_or_none(self):
        return self.thread


class _FakeSession:
    def __init__(self, thread: object | None):
        self.thread = thread
        self.committed = False
        self.deleted = False
        self.refreshed = False

    async def execute(self, _query):
        return _FakeResult(self.thread)

    async def commit(self):
        self.committed = True

    async def refresh(self, _obj):
        self.refreshed = True

    async def delete(self, _obj):
        self.deleted = True


@dataclass
class _FakeThread:
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@pytest.mark.asyncio
async def test_rename_thread_updates_title_and_commits() -> None:
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    thread = _FakeThread(id=uuid4(), user_id=user_id, title="Old", created_at=now, updated_at=now)
    db = _FakeSession(thread)

    result = await rename_thread(db, str(user_id), str(thread.id), "New title")

    assert result is not None
    assert result["title"] == "New title"
    assert db.committed is True
    assert db.refreshed is True


@pytest.mark.asyncio
async def test_rename_thread_returns_none_when_missing() -> None:
    user_id = uuid4()
    db = _FakeSession(None)

    result = await rename_thread(db, str(user_id), str(uuid4()), "Title")

    assert result is None
    assert db.committed is False


@pytest.mark.asyncio
async def test_delete_thread_deletes_and_commits() -> None:
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    thread = _FakeThread(id=uuid4(), user_id=user_id, title="Any", created_at=now, updated_at=now)
    db = _FakeSession(thread)

    deleted = await delete_thread(db, str(user_id), str(thread.id))

    assert deleted is True
    assert db.deleted is True
    assert db.committed is True


@pytest.mark.asyncio
async def test_delete_thread_returns_false_when_missing() -> None:
    user_id = uuid4()
    db = _FakeSession(None)

    deleted = await delete_thread(db, str(user_id), str(uuid4()))

    assert deleted is False
    assert db.deleted is False
