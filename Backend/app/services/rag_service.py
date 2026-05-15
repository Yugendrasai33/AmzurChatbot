from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import llm
from app.ai.memory import trim_history
from app.ai.rag.ingestion import ingest_file
from app.ai.rag.retrieval import retrieve_context
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.chat_message import ChatMessage, ChatThread
from app.schemas.rag import IngestResponse

_rag_system = (
    "You are a helpful AI assistant. Use the provided document context to answer "
    "the user's question accurately. If the context does not contain enough information, "
    "say so clearly rather than guessing."
)

_rag_prompt = ChatPromptTemplate.from_messages([
    ("system", _rag_system),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])

_rag_chain = _rag_prompt | llm | StrOutputParser()


async def ingest_attachment(
    attachment_id: str,
    user_id: str,
    db: AsyncSession,
) -> IngestResponse:
    """Load an attachment from DB, read its file, and ingest into ChromaDB."""
    result = await db.execute(
        select(Attachment).where(
            Attachment.id == UUID(attachment_id),
            Attachment.user_id == UUID(user_id),
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found.",
        )

    file_path = Path(settings.UPLOAD_DIR) / attachment.stored_path

    chunks = await ingest_file(
        file_path=str(file_path),
        attachment_id=attachment_id,
        user_id=user_id,
        mime_type=attachment.mime_type,
        type_category=attachment.type_category,
        filename=attachment.filename,
    )

    return IngestResponse(attachment_id=attachment_id, chunks_ingested=chunks)


async def stream_rag_response(
    message: str,
    thread_id: UUID,
    user_id: UUID,
    user_email: str,
    db: AsyncSession,
    attachment_ids: list[str] | None = None,
) -> AsyncIterator[str]:
    """Retrieve context, stream an LLM answer, and persist both messages."""

    # 1. Retrieve relevant chunks (scoped to specific attachments if provided)
    result = await retrieve_context(message, str(user_id), attachment_ids=attachment_ids)

    if not result.texts:
        yield "I don't have any documents to search. Please upload a file first."
        return

    context_block = "\n\n---\n\n".join(result.texts)
    augmented_input = (
        f"Use the following documents to answer:\n\n{context_block}\n\n"
        f"Question: {message}"
    )
    source_filenames = list(result.sources)

    # Resolve any UUID-based source names from the DB
    if result.unresolved_attachment_ids:
        from uuid import UUID as _UUID
        uuids = [_UUID(aid) for aid in result.unresolved_attachment_ids]
        att_result = await db.execute(
            select(Attachment).where(Attachment.id.in_(uuids))
        )
        for att in att_result.scalars().all():
            if att.filename and att.filename not in source_filenames:
                source_filenames.append(att.filename)

    # 2. Load conversation history
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

    # 3. Stream LLM response
    full_response = ""
    async for token in _rag_chain.astream(
        {"input": augmented_input, "history": chat_history},
        config={"metadata": {"user_email": user_email}},
    ):
        full_response += token
        yield token

    # 3b. Emit source filenames as a special JSON event
    if source_filenames:
        yield f"[SOURCES]{json.dumps(source_filenames)}"

    # 4. Persist both messages
    user_msg = ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        role="user",
        content=message,
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
