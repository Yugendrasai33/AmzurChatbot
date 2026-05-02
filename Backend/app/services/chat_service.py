from pathlib import Path
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import llm
from app.core.config import settings
from app.models.chat_message import ChatMessage, ChatThread

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


async def get_chat_response(message: str, history: list[dict] | None = None) -> str:
    """Get a complete chat response."""
    chat_history = []
    if history:
        for msg in history:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))

    response = await _chain.ainvoke({"input": message, "history": chat_history})
    return response


async def stream_chat_response(
    message: str, history: list[dict] | None = None
) -> AsyncGenerator[str, None]:
    """Stream a chat response token-by-token."""
    chat_history = []
    if history:
        for msg in history:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))

    async for chunk in _chain.astream({"input": message, "history": chat_history}):
        yield chunk


def _format_thread(thread: ChatThread) -> dict:
    return {
        "id": str(thread.id),
        "title": thread.title,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }


def _format_message(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "thread_id": str(message.thread_id),
        "role": message.role,
        "content": message.content,
        "model": message.model,
        "created_at": message.created_at.isoformat(),
    }


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

    user_message = ChatMessage(
        thread_id=thread.id,
        user_id=UUID(user_id),
        role="user",
        content=content,
    )
    db.add(user_message)
    await db.flush()

    assistant_text = await get_chat_response(content, history=history)

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

    return {
        "thread": _format_thread(thread),
        "user_message": _format_message(user_message),
        "assistant_message": _format_message(assistant_message),
        "model": settings.LLM_MODEL,
    }
