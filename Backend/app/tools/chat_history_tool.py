"""Chat history retrieval tool — fetches messages from the database."""
from __future__ import annotations

from typing import Any
from uuid import UUID


async def execute_chat_history(
    thread_id: str,
    user_id: str,
    limit: int = 50,
) -> dict[str, Any]:
    """Retrieve chat messages for a specific thread.

    Args:
        thread_id: UUID of the chat thread
        user_id: UUID of the user (for ownership verification)
        limit: Maximum number of messages to retrieve

    Returns:
        dict with keys: success, messages, count
    """
    if not thread_id or not thread_id.strip():
        return {"success": False, "error": "thread_id is required"}

    if not user_id or not user_id.strip():
        return {"success": False, "error": "user_id is required"}

    # Validate UUIDs
    try:
        tid = UUID(thread_id.strip())
        uid = UUID(user_id.strip())
    except ValueError:
        return {"success": False, "error": "Invalid UUID format for thread_id or user_id"}

    limit = min(max(limit, 1), 200)  # clamp between 1-200

    try:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.chat_message import ChatMessage

        if SessionLocal is None:
            return {"success": False, "error": "Database not available"}

        async with SessionLocal() as session:
            rows = await session.execute(
                select(ChatMessage)
                .where(
                    ChatMessage.thread_id == tid,
                    ChatMessage.user_id == uid,
                )
                .order_by(ChatMessage.created_at.asc())
                .limit(limit)
            )
            messages = rows.scalars().all()

            result_messages = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]

        return {
            "success": True,
            "messages": result_messages,
            "count": len(result_messages),
            "thread_id": str(tid),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Chat history retrieval failed: {e}",
        }
