from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.sql_chain import (
    execute_sql_structured,
    generate_sql,
    stream_answer_from_result,
)
from app.ai.memory import trim_history
from app.core.config import settings
from app.models.chat_message import ChatMessage, ChatThread


async def stream_sql_response(
    question: str,
    thread_id: UUID,
    user_id: UUID,
    user_email: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """Generate SQL from a question, execute it, and stream a NL answer."""

    # 1. Load conversation history
    rows = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.thread_id == thread_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    db_messages = rows.scalars().all()

    raw_history = [{"role": m.role, "content": m.content} for m in db_messages]
    trimmed = trim_history(raw_history)

    chat_history = []
    for msg in trimmed:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        else:
            chat_history.append(AIMessage(content=msg["content"]))

    # 2. Generate and validate SQL
    try:
        sql_query = await generate_sql(question, chat_history, user_email)
    except ValueError as e:
        # Safety validation rejected the query
        error_msg = f"I can only answer read-only questions about the database. ({e})"
        yield error_msg
        # Persist the failed exchange
        _persist_exchange(db, thread_id, user_id, question, error_msg)
        await db.commit()
        return

    # 3. Execute the SQL
    try:
        structured = execute_sql_structured(sql_query)
        # Only send first 3 rows to the LLM as a readable preview
        row_count = len(structured["rows"])
        column_names = ", ".join(structured["columns"])
        preview_rows = structured["rows"][:3]
        if preview_rows:
            header = " | ".join(structured["columns"])
            lines = [header]
            for r in preview_rows:
                lines.append(" | ".join(r))
            sql_result_preview = "\n".join(lines)
        else:
            sql_result_preview = "(empty)"
    except Exception as e:
        error_msg = "I wasn't able to run that query against the database. Please try rephrasing your question."
        yield error_msg
        _persist_exchange(db, thread_id, user_id, question, error_msg)
        await db.commit()
        return

    # 4. Stream LLM answer from the SQL result
    full_response = ""
    async for token in stream_answer_from_result(
        question=question,
        sql_query=sql_query,
        sql_result=sql_result_preview,
        history=chat_history,
        user_email=user_email,
        row_count=row_count,
        column_names=column_names,
    ):
        full_response += token
        yield token

    # 5. Emit the SQL query and structured result as special markers
    yield f"[SQL]{json.dumps(sql_query)}"
    result_payload = {"columns": structured["columns"], "rows": structured["rows"]}
    yield f"[SQL_RESULT]{json.dumps(result_payload)}"

    # 6. Persist both messages
    user_msg = ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        role="user",
        content=question,
    )
    assistant_msg = ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        role="assistant",
        content=full_response,
        model=settings.LLM_MODEL,
    )
    db.add(user_msg)
    db.add(assistant_msg)

    # Update thread timestamp
    thread_result = await db.execute(
        select(ChatThread).where(ChatThread.id == thread_id)
    )
    thread = thread_result.scalar_one_or_none()
    if thread:
        thread.updated_at = datetime.now(timezone.utc)

    await db.commit()


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
