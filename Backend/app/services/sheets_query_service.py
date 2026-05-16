from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.sheets_agent import run_dataframe_agent
from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.services.sheets_service import load_csv, load_google_sheet, load_xlsx


def _persist_exchange(
    db: AsyncSession,
    thread_id: UUID,
    user_id: UUID,
    question: str,
    answer: str,
) -> None:
    """Add user + assistant messages to the session (caller must commit)."""
    db.add(ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        role="user",
        content=question,
    ))
    db.add(ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        role="assistant",
        content=answer,
        model=settings.LLM_MODEL,
    ))


async def stream_sheets_response(
    question: str,
    thread_id: UUID,
    user_id: UUID,
    user_email: str,
    source_type: str,
    db: AsyncSession,
    sheet_url: str | None = None,
    attachment_id: str | None = None,
    refresh: bool = False,
) -> AsyncIterator[str]:
    """Load data, run the Pandas agent, and stream the answer."""

    cache_status = "MISS"

    # 1. Load the DataFrame
    try:
        if source_type == "google_sheet":
            if not sheet_url:
                error_msg = "A sheet URL is required for Google Sheet sources."
                yield error_msg
                _persist_exchange(db, thread_id, user_id, question, error_msg)
                await db.commit()
                return
            df, modified_time, cache_status = load_google_sheet(sheet_url, refresh=refresh)

        elif source_type in ("csv", "xlsx"):
            if not attachment_id:
                error_msg = "An attachment is required for CSV/XLSX sources."
                yield error_msg
                _persist_exchange(db, thread_id, user_id, question, error_msg)
                await db.commit()
                return

            attachment_dir = Path(settings.UPLOAD_DIR) / attachment_id
            if not attachment_dir.exists():
                error_msg = "The attached file could not be found."
                yield error_msg
                _persist_exchange(db, thread_id, user_id, question, error_msg)
                await db.commit()
                return

            files = list(attachment_dir.iterdir())
            if not files:
                error_msg = "The attachment directory is empty."
                yield error_msg
                _persist_exchange(db, thread_id, user_id, question, error_msg)
                await db.commit()
                return

            file_bytes = files[0].read_bytes()
            df = load_csv(file_bytes) if source_type == "csv" else load_xlsx(file_bytes)
        else:
            error_msg = "Invalid source_type. Use 'csv', 'xlsx', or 'google_sheet'."
            yield error_msg
            _persist_exchange(db, thread_id, user_id, question, error_msg)
            await db.commit()
            return

    except Exception as e:
        error_msg = f"Failed to load data: {e}"
        yield error_msg
        _persist_exchange(db, thread_id, user_id, question, error_msg)
        await db.commit()
        return

    # 2. Run the Pandas agent
    try:
        answer = run_dataframe_agent(df, question, user_email)
    except Exception as e:
        error_msg = f"Analysis failed: {e}"
        yield error_msg
        _persist_exchange(db, thread_id, user_id, question, error_msg)
        await db.commit()
        return

    # 3. Yield the answer
    yield answer

    # 4. Emit metadata marker (includes cache status)
    meta = {"rows": len(df), "columns": list(df.columns), "cache_status": cache_status}
    yield f"[SHEET_META]{json.dumps(meta)}"

    # 5. Persist messages
    _persist_exchange(db, thread_id, user_id, question, answer)
    await db.commit()
