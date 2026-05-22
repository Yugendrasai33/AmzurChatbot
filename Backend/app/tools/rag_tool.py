"""RAG query tool — wraps the existing retrieve_context function."""
from __future__ import annotations

from typing import Any


async def execute_rag_query(
    query: str,
    user_id: str,
    k: int = 4,
    attachment_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Retrieve relevant document chunks via RAG.

    Returns:
        dict with keys: success, texts, sources, count
    """
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty", "texts": [], "sources": []}

    if not user_id or not user_id.strip():
        return {"success": False, "error": "user_id is required", "texts": [], "sources": []}

    try:
        from app.ai.rag.retrieval import retrieve_context

        result = await retrieve_context(
            query=query.strip(),
            user_id=user_id.strip(),
            k=min(max(k, 1), 20),  # clamp between 1-20
            attachment_ids=attachment_ids,
        )
        return {
            "success": True,
            "texts": result.texts,
            "sources": result.sources,
            "count": len(result.texts),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"RAG query failed: {e}",
            "texts": [],
            "sources": [],
        }
