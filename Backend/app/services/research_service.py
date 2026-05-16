"""Research service — streaming SSE response built on the LangGraph agent."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator
from uuid import UUID
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.research_agent import run_research_agent
from app.core.config import settings
from app.models.chat_message import ChatMessage

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}
MAX_RESULTS_PER_QUERY = 5
RECENCY_CUTOFF = datetime.now(timezone.utc) - timedelta(days=36 * 30)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_exchange(
    db: AsyncSession,
    thread_id: UUID,
    user_id: UUID,
    question: str,
    answer: str,
) -> None:
    """Add user + assistant messages (caller commits). KI-06 pattern."""
    db.add(ChatMessage(thread_id=thread_id, user_id=user_id, role="user", content=question))
    db.add(
        ChatMessage(
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=answer,
            model=settings.LLM_MODEL,
        )
    )


# ---------------------------------------------------------------------------
# arXiv client
# ---------------------------------------------------------------------------

def _parse_arxiv_atom(xml_text: str) -> list[dict[str, Any]]:
    """Defensive Atom parsing — never trust raw fields."""
    out: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    for entry in root.findall("a:entry", ARXIV_NS):
        eid_el = entry.find("a:id", ARXIV_NS)
        title_el = entry.find("a:title", ARXIV_NS)
        summary_el = entry.find("a:summary", ARXIV_NS)
        published_el = entry.find("a:published", ARXIV_NS)

        url = (eid_el.text or "").strip() if eid_el is not None else ""
        # Extract bare arxiv id (e.g. 2401.12345v1 -> 2401.12345)
        m = re.search(r"abs/([0-9.]+)(v\d+)?", url)
        arxiv_id = m.group(1) if m else url.rsplit("/", 1)[-1]
        title = re.sub(r"\s+", " ", (title_el.text or "").strip()) if title_el is not None else ""
        summary = re.sub(r"\s+", " ", (summary_el.text or "").strip()) if summary_el is not None else ""

        authors: list[str] = []
        for a in entry.findall("a:author", ARXIV_NS):
            name_el = a.find("a:name", ARXIV_NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        year = ""
        published = (published_el.text or "").strip() if published_el is not None else ""
        if published:
            year = published[:4]

        if not title or not arxiv_id:
            continue

        out.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "year": year,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "summary": summary,
                "published": published,
            }
        )
    return out


async def _search_arxiv(query: str) -> list[dict[str, Any]]:
    """Search arXiv and prefer recent papers (last 36 months) by sorting client-side."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": MAX_RESULTS_PER_QUERY * 2,  # over-fetch for recency filter
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": "AmzurAIChat/1.0 (research-agent)"}) as client:
        resp = await client.get(ARXIV_API, params=params)
        resp.raise_for_status()
        papers = _parse_arxiv_atom(resp.text)

    # Prefer last 36 months without dropping older relevant work entirely.
    def _is_recent(p: dict[str, Any]) -> bool:
        pub = p.get("published", "")
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            return dt >= RECENCY_CUTOFF
        except Exception:
            return False

    recent = [p for p in papers if _is_recent(p)]
    older = [p for p in papers if not _is_recent(p)]
    ordered = recent + older
    return ordered[:MAX_RESULTS_PER_QUERY]


# ---------------------------------------------------------------------------
# Streaming service
# ---------------------------------------------------------------------------

def _assemble_digest(sections: dict[str, str]) -> str:
    """Stitch all sections into a single markdown blob for DB persistence."""
    titles = [
        ("overview", "## Overview"),
        ("key_papers", "## Key papers"),
        ("themes", "## Emerging themes"),
        ("gaps", "## Open challenges"),
        ("future", "## Future directions"),
        ("references", "## References"),
    ]
    parts: list[str] = []
    for sid, heading in titles:
        body = sections.get(sid)
        if body:
            parts.append(f"{heading}\n\n{body}")
    return "\n\n".join(parts) if parts else "_No digest produced._"


async def stream_research_response(
    topic: str,
    thread_id: UUID,
    user_id: UUID,
    user_email: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """Yield newline-delimited JSON event strings plus a final [DONE] marker.

    The router wraps each yielded string as `data: <str>\\n\\n`.
    """
    sections: dict[str, str] = {}
    total_papers = 0
    coverage = 0

    try:
        async for event in run_research_agent(topic, user_email, _search_arxiv):
            yield json.dumps(event, ensure_ascii=False)

            etype = event.get("event")
            if etype == "section":
                sections[event["id"]] = event["content"]
            elif etype == "done":
                total_papers = int(event.get("total_papers", 0))
                coverage = int(event.get("coverage", 0))
    except Exception as exc:
        err = {
            "event": "section",
            "id": "error",
            "title": "Error",
            "content": f"Research failed: {exc}",
        }
        yield json.dumps(err)
        _persist_exchange(db, thread_id, user_id, topic, f"Research failed: {exc}")
        await db.commit()
        return

    digest_md = _assemble_digest(sections)
    footer = f"\n\n---\n_{total_papers} papers · {coverage}% coverage_"
    _persist_exchange(db, thread_id, user_id, topic, digest_md + footer)
    await db.commit()
