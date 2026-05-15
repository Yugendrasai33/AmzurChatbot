"""
Unit tests for the NL-to-SQL pipeline: sql_utils, sql_safety, sql_service.
LLM and DB are mocked — no real API calls or database connections.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.chains.sql_safety import is_table_allowed, validate_sql
from app.ai.chains.sql_utils import _build_sync_db_url
from app.core.config import settings


# ---------------------------------------------------------------------------
# _build_sync_db_url
# ---------------------------------------------------------------------------

class TestBuildSyncDbUrl:

    def test_converts_asyncpg_to_psycopg2(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            settings, "DATABASE_URL",
            "postgresql+asyncpg://user:pass@localhost:5432/mydb",
        )
        result = _build_sync_db_url()
        assert result == "postgresql+psycopg2://user:pass@localhost:5432/mydb"

    def test_raises_when_database_url_is_none(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(settings, "DATABASE_URL", None)
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            _build_sync_db_url()


# ---------------------------------------------------------------------------
# validate_sql
# ---------------------------------------------------------------------------

class TestValidateSql:

    @pytest.mark.parametrize("keyword", [
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
        "insert", "update", "delete", "drop", "truncate", "alter",
        "Insert", "Update", "Delete", "Drop", "Truncate", "Alter",
    ])
    def test_blocks_all_keywords_case_insensitive(self, keyword: str):
        query = f"{keyword} INTO some_table VALUES (1)"
        with pytest.raises(ValueError, match="Write operations are not allowed"):
            validate_sql(query)

    def test_allows_select_query(self):
        query = "SELECT id, email FROM profiles WHERE email LIKE '%@example.com'"
        result = validate_sql(query)
        assert result == query

    def test_allows_updated_at_column_name(self):
        """Columns like 'updated_at' should NOT trigger the UPDATE blocker."""
        query = "SELECT id, updated_at FROM chat_threads ORDER BY updated_at DESC"
        result = validate_sql(query)
        assert result == query

    def test_allows_deleted_flag_column(self):
        """A column called 'deleted' should NOT trigger the DELETE blocker."""
        query = "SELECT id FROM profiles WHERE deleted = false"
        result = validate_sql(query)
        assert result == query

    def test_blocks_drop_table(self):
        with pytest.raises(ValueError):
            validate_sql("DROP TABLE profiles;")

    def test_blocks_delete_from(self):
        with pytest.raises(ValueError):
            validate_sql("DELETE FROM chat_messages WHERE id = '123'")

    def test_blocks_alter_table(self):
        with pytest.raises(ValueError):
            validate_sql("ALTER TABLE profiles ADD COLUMN foo TEXT")

    def test_blocks_truncate(self):
        with pytest.raises(ValueError):
            validate_sql("TRUNCATE chat_messages")

    def test_returns_query_unchanged_when_safe(self):
        query = "SELECT COUNT(*) FROM chat_messages"
        assert validate_sql(query) is query


# ---------------------------------------------------------------------------
# is_table_allowed
# ---------------------------------------------------------------------------

class TestIsTableAllowed:

    def test_allowed_tables(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            settings, "SQL_QUERY_ALLOWED_TABLES",
            "chat_threads,chat_messages,profiles,attachments",
        )
        # Re-import to pick up the new setting
        from app.ai.chains.sql_safety import get_allowed_tables
        allowed = get_allowed_tables()

        assert "chat_threads" in allowed
        assert "profiles" in allowed
        assert "attachments" in allowed

    def test_disallowed_table(self):
        assert is_table_allowed("secret_admin_table") is False

    def test_allowed_table(self):
        assert is_table_allowed("profiles") is True

    def test_case_insensitive(self):
        assert is_table_allowed("PROFILES") is True


# ---------------------------------------------------------------------------
# stream_sql_response (service layer)
# ---------------------------------------------------------------------------

class TestStreamSqlResponse:

    @pytest.mark.asyncio
    async def test_persists_both_messages_on_success(self):
        from app.services.sql_service import stream_sql_response

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Mock the thread lookup for timestamp update
        mock_thread_result = MagicMock()
        mock_thread_result.scalar_one_or_none.return_value = None

        # First call: message history, second call: thread lookup
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result
            return mock_thread_result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        with patch("app.services.sql_service.generate_sql", new_callable=AsyncMock) as mock_gen, \
             patch("app.services.sql_service.execute_sql") as mock_exec, \
             patch("app.services.sql_service.stream_answer_from_result") as mock_stream:

            mock_gen.return_value = "SELECT COUNT(*) FROM profiles"
            mock_exec.return_value = "[(5,)]"

            async def fake_stream(*a, **kw):
                yield "There are "
                yield "5 profiles."

            mock_stream.return_value = fake_stream()

            tokens = []
            async for token in stream_sql_response(
                question="How many users?",
                thread_id=uuid4(),
                user_id=uuid4(),
                user_email="test@test.com",
                db=mock_db,
            ):
                tokens.append(token)

            # Should have streamed tokens + SQL marker
            assert any("There are" in t for t in tokens)
            assert any("[SQL]" in t for t in tokens)

            # Should have added 2 messages (user + assistant)
            assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_safety_rejection_yields_friendly_message(self):
        from app.services.sql_service import stream_sql_response

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.sql_service.generate_sql", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ValueError("Blocked keyword detected: DROP")

            tokens = []
            async for token in stream_sql_response(
                question="Drop the profiles table",
                thread_id=uuid4(),
                user_id=uuid4(),
                user_email="test@test.com",
                db=mock_db,
            ):
                tokens.append(token)

            full = "".join(tokens)
            assert "read-only" in full.lower()
