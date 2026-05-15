"""
Unit tests for the RAG pipeline: ingest_file, retrieve_context, ingest_attachment.

Embeddings are mocked so no real LLM calls are made.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.rag.ingestion import ingest_file
from app.ai.rag.retrieval import RetrievalResult, retrieve_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_embeddings(texts: list[str]) -> list[list[float]]:
    """Return deterministic fake embeddings (128-dim) for each text."""
    return [[float(i)] * 128 for i in range(len(texts))]


def _fake_embed_query(text: str) -> list[float]:
    """Return a deterministic fake query embedding."""
    return [0.5] * 128


# ---------------------------------------------------------------------------
# ingest_file
# ---------------------------------------------------------------------------

class TestIngestFile:
    """Tests for app.ai.rag.ingestion.ingest_file."""

    @pytest.mark.asyncio
    async def test_skips_video_category(self):
        """Files with type_category='video' should return 0 chunks."""
        result = await ingest_file(
            file_path="/nonexistent.mp4",
            attachment_id=str(uuid4()),
            user_id=str(uuid4()),
            type_category="video",
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_skips_image_category(self):
        """Files with type_category='image' should return 0 chunks."""
        result = await ingest_file(
            file_path="/nonexistent.png",
            attachment_id=str(uuid4()),
            user_id=str(uuid4()),
            type_category="image",
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_skips_generated_image_category(self):
        """Files with type_category='generated_image' should return 0 chunks."""
        result = await ingest_file(
            file_path="/nonexistent.png",
            attachment_id=str(uuid4()),
            user_id=str(uuid4()),
            type_category="generated_image",
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_for_missing_file(self):
        """If the file does not exist on disk, return 0."""
        result = await ingest_file(
            file_path="/definitely/does/not/exist.txt",
            attachment_id=str(uuid4()),
            user_id=str(uuid4()),
            mime_type="text/plain",
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_ingests_text_file(self, tmp_path: Path):
        """A valid text file should be chunked, embedded, and stored in ChromaDB."""
        # Create a temp text file with enough content to produce chunks
        text_file = tmp_path / "sample.txt"
        text_file.write_text("The company remote work policy allows 3 days from home. " * 50)

        user_id = str(uuid4())
        attachment_id = str(uuid4())

        fake_collection = MagicMock()
        fake_collection.upsert = MagicMock()

        with patch("app.ai.rag.ingestion.embeddings") as mock_emb, \
             patch("app.ai.rag.ingestion.get_user_collection", return_value=fake_collection):
            mock_emb.aembed_documents = AsyncMock(side_effect=_fake_embeddings)

            result = await ingest_file(
                file_path=str(text_file),
                attachment_id=attachment_id,
                user_id=user_id,
                mime_type="text/plain",
                filename="sample.txt",
            )

        assert result > 0
        fake_collection.upsert.assert_called_once()
        call_kwargs = fake_collection.upsert.call_args
        # Verify IDs follow the naming convention
        ids = call_kwargs.kwargs.get("ids") or call_kwargs[1].get("ids")
        assert all(id_.startswith(f"{attachment_id}_chunk_") for id_ in ids)
        # Verify metadata includes attachment_id and user_id
        metadatas = call_kwargs.kwargs.get("metadatas") or call_kwargs[1].get("metadatas")
        for meta in metadatas:
            assert meta["attachment_id"] == attachment_id
            assert meta["user_id"] == user_id
            assert meta["filename"] == "sample.txt"

    @pytest.mark.asyncio
    async def test_ingests_empty_file_returns_zero(self, tmp_path: Path):
        """An empty file should produce 0 chunks."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        user_id = str(uuid4())

        with patch("app.ai.rag.ingestion.embeddings") as mock_emb, \
             patch("app.ai.rag.ingestion.get_user_collection"):
            mock_emb.aembed_documents = AsyncMock(return_value=[])

            result = await ingest_file(
                file_path=str(empty_file),
                attachment_id=str(uuid4()),
                user_id=user_id,
                mime_type="text/plain",
            )

        assert result == 0


# ---------------------------------------------------------------------------
# retrieve_context
# ---------------------------------------------------------------------------

class TestRetrieveContext:
    """Tests for app.ai.rag.retrieval.retrieve_context."""

    @pytest.mark.asyncio
    async def test_empty_collection_returns_empty(self):
        """When the user's collection has no documents, return empty result."""
        fake_collection = MagicMock()
        fake_collection.count.return_value = 0

        with patch("app.ai.rag.retrieval.get_user_collection", return_value=fake_collection), \
             patch("app.ai.rag.retrieval.embeddings"):
            result = await retrieve_context("test query", str(uuid4()))

        assert isinstance(result, RetrievalResult)
        assert result.texts == []
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_returns_texts_and_sources(self):
        """Should return chunk texts and deduplicated source filenames."""
        fake_collection = MagicMock()
        fake_collection.count.return_value = 2
        fake_collection.query.return_value = {
            "documents": [["chunk one text", "chunk two text"]],
            "metadatas": [[
                {"filename": "report.pdf", "attachment_id": "a1", "file_path": "/uploads/report.pdf"},
                {"filename": "report.pdf", "attachment_id": "a1", "file_path": "/uploads/report.pdf"},
            ]],
        }

        with patch("app.ai.rag.retrieval.get_user_collection", return_value=fake_collection), \
             patch("app.ai.rag.retrieval.embeddings") as mock_emb:
            mock_emb.aembed_query = AsyncMock(return_value=_fake_embed_query("test"))

            result = await retrieve_context("test query", str(uuid4()))

        assert len(result.texts) == 2
        assert result.texts[0] == "chunk one text"
        # Sources should be deduplicated
        assert result.sources == ["report.pdf"]

    @pytest.mark.asyncio
    async def test_attachment_id_filter_single(self):
        """When a single attachment_id is provided, where filter uses equality."""
        fake_collection = MagicMock()
        fake_collection.count.return_value = 5
        fake_collection.query.return_value = {
            "documents": [["filtered chunk"]],
            "metadatas": [[{"filename": "file.txt", "attachment_id": "att-1"}]],
        }

        with patch("app.ai.rag.retrieval.get_user_collection", return_value=fake_collection), \
             patch("app.ai.rag.retrieval.embeddings") as mock_emb:
            mock_emb.aembed_query = AsyncMock(return_value=_fake_embed_query("q"))

            result = await retrieve_context("q", str(uuid4()), attachment_ids=["att-1"])

        call_kwargs = fake_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"attachment_id": "att-1"}
        assert len(result.texts) == 1

    @pytest.mark.asyncio
    async def test_attachment_id_filter_multiple(self):
        """When multiple attachment_ids are provided, where filter uses $in."""
        fake_collection = MagicMock()
        fake_collection.count.return_value = 10
        fake_collection.query.return_value = {
            "documents": [["a", "b"]],
            "metadatas": [[
                {"filename": "a.txt", "attachment_id": "att-1"},
                {"filename": "b.txt", "attachment_id": "att-2"},
            ]],
        }

        with patch("app.ai.rag.retrieval.get_user_collection", return_value=fake_collection), \
             patch("app.ai.rag.retrieval.embeddings") as mock_emb:
            mock_emb.aembed_query = AsyncMock(return_value=_fake_embed_query("q"))

            result = await retrieve_context("q", str(uuid4()), attachment_ids=["att-1", "att-2"])

        call_kwargs = fake_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"attachment_id": {"$in": ["att-1", "att-2"]}}

    @pytest.mark.asyncio
    async def test_never_raises_returns_empty_on_error(self):
        """On any exception, retrieve_context should return empty, not raise."""
        with patch("app.ai.rag.retrieval.get_user_collection", side_effect=RuntimeError("boom")):
            result = await retrieve_context("test", str(uuid4()))

        assert isinstance(result, RetrievalResult)
        assert result.texts == []
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_uuid_filenames_marked_unresolved(self):
        """Filenames that are UUID-based should be placed in unresolved_attachment_ids."""
        fake_collection = MagicMock()
        fake_collection.count.return_value = 1
        fake_collection.query.return_value = {
            "documents": [["some chunk"]],
            "metadatas": [[{
                "filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
                "attachment_id": "att-uuid",
                "file_path": "/uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
            }]],
        }

        with patch("app.ai.rag.retrieval.get_user_collection", return_value=fake_collection), \
             patch("app.ai.rag.retrieval.embeddings") as mock_emb:
            mock_emb.aembed_query = AsyncMock(return_value=_fake_embed_query("q"))

            result = await retrieve_context("q", str(uuid4()))

        assert "att-uuid" in result.unresolved_attachment_ids
        # UUID filename should not appear in sources
        assert len(result.sources) == 0


# ---------------------------------------------------------------------------
# ingest_attachment (service layer)
# ---------------------------------------------------------------------------

class TestIngestAttachment:
    """Tests for app.services.rag_service.ingest_attachment."""

    @pytest.mark.asyncio
    async def test_raises_404_for_missing_attachment(self):
        """When the attachment doesn't exist in DB, should raise HTTPException 404."""
        from unittest.mock import AsyncMock as AM
        from app.services.rag_service import ingest_attachment
        from fastapi import HTTPException

        mock_db = AM()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AM(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await ingest_attachment(
                attachment_id=str(uuid4()),
                user_id=str(uuid4()),
                db=mock_db,
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_calls_ingest_file_with_attachment_data(self):
        """Should pass attachment fields to ingest_file and return IngestResponse."""
        from unittest.mock import AsyncMock as AM
        from app.services.rag_service import ingest_attachment

        att_id = str(uuid4())
        user_id = str(uuid4())

        fake_attachment = MagicMock()
        fake_attachment.stored_path = "some/path/file.pdf"
        fake_attachment.mime_type = "application/pdf"
        fake_attachment.type_category = "pdf"
        fake_attachment.filename = "report.pdf"

        mock_db = AM()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_attachment
        mock_db.execute = AM(return_value=mock_result)

        with patch("app.services.rag_service.ingest_file", new_callable=AM) as mock_ingest:
            mock_ingest.return_value = 5

            response = await ingest_attachment(att_id, user_id, mock_db)

        assert response.attachment_id == att_id
        assert response.chunks_ingested == 5
        mock_ingest.assert_called_once()
        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["attachment_id"] == att_id
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["mime_type"] == "application/pdf"
        assert call_kwargs["filename"] == "report.pdf"
