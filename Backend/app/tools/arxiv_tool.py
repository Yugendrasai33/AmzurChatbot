"""arXiv search tool — wraps the existing _search_arxiv function from research_service."""
from __future__ import annotations

from typing import Any


async def execute_arxiv_search(query: str) -> dict[str, Any]:
    """Search arXiv for papers matching the query.

    Returns:
        dict with keys: success, papers (list), count
    """
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty", "papers": [], "count": 0}

    try:
        from app.services.research_service import _search_arxiv

        papers = await _search_arxiv(query.strip())
        return {
            "success": True,
            "papers": papers,
            "count": len(papers),
            "query": query.strip(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"arXiv search failed: {e}",
            "papers": [],
            "count": 0,
        }
