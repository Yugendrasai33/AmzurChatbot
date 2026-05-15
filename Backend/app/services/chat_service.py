from pathlib import Path
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

import base64

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import llm
from app.ai.memory import trim_history
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.chat_message import ChatMessage, ChatThread
from app.services.attachment_service import (
    extract_text_content,
    format_attachment_meta,
    get_attachments_by_ids,
    get_file_path,
    link_attachments_to_message,
)

# Load system prompt from file
_prompt_path = Path(__file__).parent.parent / "ai" / "prompts" / "chat_system.txt"
_system_prompt = _prompt_path.read_text().strip()

# LCEL chain: prompt | llm | parser
_chat_prompt = ChatPromptTemplate.from_messages([
    ("system", _system_prompt),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])

_chain = _chat_prompt | llm | StrOutputParser()

_title_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Generate a short and clear title for a chat thread from the user's first message. "
        "Return only the title, maximum 8 words, no quotes.",
    ),
    ("human", "{input}"),
])

_title_chain = _title_prompt | llm | StrOutputParser()


def _fallback_thread_title(message: str) -> str:
    return (message[:40].strip() or "New chat")


async def generate_thread_title(message: str) -> str:
    try:
        title = await _title_chain.ainvoke({"input": message})
        cleaned = " ".join(title.split()).strip().strip('"').strip("'")
        return cleaned[:80] if cleaned else _fallback_thread_title(message)
    except Exception:
        return _fallback_thread_title(message)


async def get_chat_response(message: "str | list[dict]", history: list[dict] | None = None) -> str:
    """Get a complete chat response. Supports plain-text and multimodal (image/video) input."""
    chat_history = []
    if history:
        trimmed = trim_history(history)
        for msg in trimmed:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))

    if isinstance(message, list):
        # Multimodal path: call the LLM directly with system + history + rich human message
        messages = [SystemMessage(content=_system_prompt)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=message))
        result = await llm.ainvoke(messages)
        raw = result.content
        # result.content may be a list of content blocks from some model versions
        if isinstance(raw, list):
            return " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw
            ).strip()
        return str(raw)

    # Text-only path: use the existing LCEL chain
    response = await _chain.ainvoke({"input": message, "history": chat_history})
    return response


async def stream_chat_response(
    message: str, history: list[dict] | None = None
) -> AsyncGenerator[str, None]:
    """Stream a chat response token-by-token."""
    chat_history = []
    if history:
        trimmed = trim_history(history)
        for msg in trimmed:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))

    async for chunk in _chain.astream({"input": message, "history": chat_history}):
        yield chunk


# Inline size limit for video base64 (bytes). Above this, fall back to a note.
_VIDEO_INLINE_LIMIT = 10 * 1024 * 1024  # 10 MB


def _build_multimodal_content(
    message: str,
    attachments: list[Attachment],
) -> "str | list[dict]":
    """
    Return the LLM input for the given message + attachments.

    - Text-extractable files (code, pdf, table): prepended as plain text.
    - Images: embedded as base64 data-URL in a multimodal content list.
    - Videos ≤ 10 MB: embedded as base64 data-URL (Gemini supports inline video).
    - Videos > 10 MB: described as a note (too large to embed inline).

    Returns a plain string when there are no visual attachments, or a
    list[dict] (OpenAI-compatible multimodal content) when images/video are present.
    """
    if not attachments:
        return message

    text_parts: list[str] = []
    media_parts: list[dict] = []

    for att in attachments:
        if att.type_category in ("code", "pdf", "table"):
            extracted = extract_text_content(att)
            if extracted:
                text_parts.append(f"[Attached file: {att.filename}]\n```\n{extracted}\n```")

        elif att.type_category == "image":
            try:
                file_path = get_file_path(att)
                data = file_path.read_bytes()
                b64 = base64.b64encode(data).decode("ascii")
                media_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{att.mime_type};base64,{b64}"},
                })
            except Exception:
                text_parts.append(f"[Image attached: {att.filename} — file could not be read]")

        elif att.type_category == "video":
            try:
                file_path = get_file_path(att)
                size = file_path.stat().st_size
                if size <= _VIDEO_INLINE_LIMIT:
                    data = file_path.read_bytes()
                    b64 = base64.b64encode(data).decode("ascii")
                    # LiteLLM/Gemini accepts video via the image_url slot with a video MIME
                    media_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{att.mime_type};base64,{b64}"},
                    })
                else:
                    mb = size / (1024 * 1024)
                    text_parts.append(
                        f"[Video attached: {att.filename} ({mb:.1f} MB) — "
                        "file too large to analyse inline; describe what you can see if shared elsewhere]"
                    )
            except Exception:
                text_parts.append(f"[Video attached: {att.filename} — file could not be read]")

    # If no visual media present, return plain text (keeps existing behaviour)
    if not media_parts:
        context = "\n\n".join(text_parts)
        return f"{context}\n\nUser message: {message}" if context else message

    # Build OpenAI-compatible multimodal content list
    text_context = "\n\n".join(text_parts)
    user_text = f"{text_context}\n\nUser message: {message}" if text_context else message
    content: list[dict] = [{"type": "text", "text": user_text}]
    content.extend(media_parts)
    return content


def _format_thread(thread: ChatThread) -> dict:
    return {
        "id": str(thread.id),
        "title": thread.title,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }


def _format_message(message: ChatMessage) -> dict:
    result = {
        "id": str(message.id),
        "thread_id": str(message.thread_id),
        "role": message.role,
        "content": message.content,
        "model": message.model,
        "created_at": message.created_at.isoformat(),
    }
    state = inspect(message)
    if "attachments" not in state.unloaded and message.attachments:
        result["attachments"] = [format_attachment_meta(a) for a in message.attachments]
    return result


async def list_threads(db: AsyncSession, user_id: str) -> list[dict]:
    query = (
        select(ChatThread)
        .where(ChatThread.user_id == UUID(user_id))
        .order_by(ChatThread.updated_at.desc())
    )
    result = await db.execute(query)
    return [_format_thread(thread) for thread in result.scalars().all()]


async def create_thread(db: AsyncSession, user_id: str, title: str | None = None) -> dict:
    thread = ChatThread(user_id=UUID(user_id), title=(title or "New chat").strip() or "New chat")
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return _format_thread(thread)


async def rename_thread(db: AsyncSession, user_id: str, thread_id: str, title: str) -> dict | None:
    thread_query = select(ChatThread).where(
        ChatThread.id == UUID(thread_id),
        ChatThread.user_id == UUID(user_id),
    )
    thread = (await db.execute(thread_query)).scalar_one_or_none()
    if not thread:
        return None

    thread.title = title.strip() or thread.title
    thread.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(thread)
    return _format_thread(thread)


async def delete_thread(db: AsyncSession, user_id: str, thread_id: str) -> bool:
    thread_query = select(ChatThread).where(
        ChatThread.id == UUID(thread_id),
        ChatThread.user_id == UUID(user_id),
    )
    thread = (await db.execute(thread_query)).scalar_one_or_none()
    if not thread:
        return False

    await db.delete(thread)
    await db.commit()
    return True


async def get_thread_messages(db: AsyncSession, user_id: str, thread_id: str) -> list[dict]:
    from sqlalchemy.orm import selectinload

    thread_uuid = UUID(thread_id)
    thread_query = select(ChatThread).where(
        ChatThread.id == thread_uuid,
        ChatThread.user_id == UUID(user_id),
    )
    thread = (await db.execute(thread_query)).scalar_one_or_none()
    if not thread:
        return []

    messages_query = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.attachments))
        .where(ChatMessage.thread_id == thread_uuid, ChatMessage.user_id == UUID(user_id))
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(messages_query)
    return [_format_message(message) for message in result.scalars().all()]


async def send_message_with_persistence(
    db: AsyncSession,
    user_id: str,
    content: str,
    thread_id: str | None = None,
    attachment_ids: list[str] | None = None,
) -> dict:
    if thread_id:
        thread_query = select(ChatThread).where(
            ChatThread.id == UUID(thread_id),
            ChatThread.user_id == UUID(user_id),
        )
        thread = (await db.execute(thread_query)).scalar_one_or_none()
    else:
        thread = None

    if not thread:
        title = await generate_thread_title(content)
        thread = ChatThread(
            user_id=UUID(user_id),
            title=title,
        )
        db.add(thread)
        await db.flush()

    history_query = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread.id, ChatMessage.user_id == UUID(user_id))
        .order_by(ChatMessage.created_at.asc())
    )
    history_result = await db.execute(history_query)
    history_rows = history_result.scalars().all()
    history = [{"role": row.role, "content": row.content} for row in history_rows]
    history = trim_history(history)

    user_message = ChatMessage(
        thread_id=thread.id,
        user_id=UUID(user_id),
        role="user",
        content=content,
    )
    db.add(user_message)
    await db.flush()

    # Process attachments
    attachments: list[Attachment] = []
    if attachment_ids:
        attachments = await get_attachments_by_ids(db, attachment_ids, user_id)
        await link_attachments_to_message(db, attachment_ids, user_message.id)

    # Build the AI input with attachment context (multimodal when images/video present)
    ai_input = _build_multimodal_content(content, attachments)

    assistant_text = await get_chat_response(ai_input, history=history)

    assistant_message = ChatMessage(
        thread_id=thread.id,
        user_id=UUID(user_id),
        role="assistant",
        content=assistant_text,
        model=settings.LLM_MODEL,
    )
    db.add(assistant_message)
    thread.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(thread)
    await db.refresh(user_message)
    await db.refresh(assistant_message)

    # Reload attachments for response
    if attachment_ids:
        from sqlalchemy.orm import selectinload
        msg_query = select(ChatMessage).options(selectinload(ChatMessage.attachments)).where(
            ChatMessage.id == user_message.id
        )
        user_message = (await db.execute(msg_query)).scalar_one()

    return {
        "thread": _format_thread(thread),
        "user_message": _format_message(user_message),
        "assistant_message": _format_message(assistant_message),
        "model": settings.LLM_MODEL,
    }
