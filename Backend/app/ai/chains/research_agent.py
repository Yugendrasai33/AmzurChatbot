"""ResearchDigestAgent — LangGraph multi-step orchestration.

Nodes:  decompose_topic -> search_arxiv -> evaluate_coverage -> (loop) -> synthesize_digest

LLM steps use LCEL (prompt | llm | parser). All external arXiv I/O lives in the
service layer (research_service.py) and is injected via the state's `search_fn`
so this module stays unit-testable and free of HTTP concerns.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, TypedDict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from app.ai.llm import llm
from app.core.config import settings

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


_DECOMPOSE_TEMPLATE = ChatPromptTemplate.from_template(_load_prompt("research_decompose.txt"))
_SYNTHESIZE_TEMPLATE = ChatPromptTemplate.from_template(_load_prompt("research_synthesize.txt"))

decompose_chain = _DECOMPOSE_TEMPLATE | llm | StrOutputParser()
synthesize_chain = _SYNTHESIZE_TEMPLATE | llm | StrOutputParser()


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class ResearchState(TypedDict, total=False):
    topic: str
    user_email: str
    queries: list[str]            # queries planned for this round
    used_queries: list[str]
    papers: list[dict[str, Any]]  # accumulated, deduped by arxiv_id
    rounds: int
    coverage: int
    events: list[dict[str, Any]]  # emitted per-step, drained by caller
    sections: dict[str, str]      # filled by synthesize node
    search_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]  # injected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_ROUNDS = 4
COVERAGE_THRESHOLD = 80


def _config(user_email: str) -> dict[str, Any]:
    return {
        "metadata": {
            "user_email": user_email,
            "application": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        }
    }


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Best-effort JSON extraction — strips ```json fences if present."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip("`").strip()
    # Trim to first { and last }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    return json.loads(s)


def _dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in papers:
        key = p.get("arxiv_id") or p.get("url") or p.get("title", "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _score_coverage(papers: list[dict[str, Any]]) -> tuple[int, list[str]]:
    """Heuristic 0-100 coverage score + list of gap labels."""
    n = len(papers)
    if n == 0:
        return 0, ["background", "current SOTA", "open challenges", "future direction"]

    blob = " ".join(((p.get("title", "") + " " + p.get("summary", "")).lower()) for p in papers)

    facets = {
        "background": ["survey", "overview", "introduction", "tutorial", "review"],
        "current SOTA": ["state-of-the-art", "sota", "benchmark", "outperform", "achieve"],
        "open challenges": ["challenge", "limitation", "open problem", "remains", "difficult"],
        "future direction": ["future work", "future direction", "we propose", "promising", "next step"],
    }
    hit = {name: any(k in blob for k in kws) for name, kws in facets.items()}

    # Paper-count component (0-60), facet component (0-40)
    paper_score = min(60, int(60 * n / 10))  # saturates at 10 papers
    facet_score = int(40 * sum(hit.values()) / len(facets))
    score = min(100, paper_score + facet_score)

    gaps = [name for name, ok in hit.items() if not ok]
    return score, gaps


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def _decompose_node(state: ResearchState) -> ResearchState:
    round_no = state.get("rounds", 0) + 1
    raw = await decompose_chain.ainvoke(
        {
            "topic": state["topic"],
            "round": round_no,
            "used_queries": json.dumps(state.get("used_queries", [])),
            "collected_titles": json.dumps([p.get("title", "") for p in state.get("papers", [])]),
            "gaps": json.dumps(_score_coverage(state.get("papers", []))[1]),
        },
        config=_config(state["user_email"]),
    )
    try:
        obj = _parse_json_object(raw)
        queries = [str(q).strip() for q in obj.get("queries", []) if str(q).strip()]
    except Exception:
        queries = [state["topic"]]

    # On the final allowed round, force a single targeted gap query.
    if round_no >= MAX_ROUNDS:
        queries = queries[:1] or [state["topic"]]
    queries = queries[:4] or [state["topic"]]

    events = list(state.get("events", []))
    events.append({"event": "status", "message": f"Planned {len(queries)} arXiv query(ies) for round {round_no}"})

    return {**state, "queries": queries, "rounds": round_no, "events": events}


async def _search_node(state: ResearchState) -> ResearchState:
    events = list(state.get("events", []))
    papers = list(state.get("papers", []))
    used = list(state.get("used_queries", []))
    search_fn = state["search_fn"]

    for q in state.get("queries", []):
        events.append({"event": "status", "message": f"Searching arXiv for: {q}"})
        try:
            results = await search_fn(q)
        except Exception as exc:  # pragma: no cover - surfaced as status
            events.append({"event": "status", "message": f"arXiv query failed: {exc}"})
            results = []
        papers.extend(results)
        used.append(q)

    papers = _dedupe_papers(papers)
    events.append({"event": "status", "message": f"Total distinct papers collected: {len(papers)}"})
    return {**state, "papers": papers, "used_queries": used, "events": events}


async def _evaluate_node(state: ResearchState) -> ResearchState:
    score, _gaps = _score_coverage(state.get("papers", []))
    events = list(state.get("events", []))
    events.append({"event": "status", "message": f"Evidence coverage: {score}% (round {state.get('rounds', 0)})"})
    return {**state, "coverage": score, "events": events}


def _route_after_eval(state: ResearchState) -> str:
    rounds = state.get("rounds", 0)
    coverage = state.get("coverage", 0)
    papers = state.get("papers", [])
    if coverage >= COVERAGE_THRESHOLD and len(papers) >= 8:
        return "synthesize"
    if rounds >= MAX_ROUNDS:
        return "synthesize"
    return "decompose"


async def _synthesize_node(state: ResearchState) -> ResearchState:
    papers = state.get("papers", [])
    events = list(state.get("events", []))
    events.append({"event": "status", "message": "Synthesizing digest…"})

    # References are deterministic — no LLM needed.
    references_md = "\n".join(
        f"{i+1}. [{p.get('title', 'Untitled')}]({p.get('url', '')}) — {', '.join(p.get('authors', []))} ({p.get('year', 'n.d.')})"
        for i, p in enumerate(papers)
    ) or "_No papers available._"

    coverage = state.get("coverage", 0)
    if not papers:
        sections = {
            "overview": "_No arXiv results were returned for this topic. The digest below is unavailable._",
            "key_papers": "_No papers._",
            "themes": "_No themes — insufficient evidence._",
            "gaps": "_Unable to assess._",
            "future": "_Unable to suggest directions._",
            "references": references_md,
        }
        return {**state, "sections": sections, "events": events}

    raw = await synthesize_chain.ainvoke(
        {
            "topic": state["topic"],
            "coverage": coverage,
            "papers_json": json.dumps(
                [
                    {
                        "title": p.get("title", ""),
                        "authors": p.get("authors", []),
                        "year": p.get("year", ""),
                        "url": p.get("url", ""),
                        "summary": (p.get("summary", "") or "")[:1200],
                    }
                    for p in papers
                ],
                indent=2,
            ),
        },
        config=_config(state["user_email"]),
    )

    try:
        parsed = _parse_json_object(raw)
    except Exception:
        parsed = {}

    sections = {
        "overview": str(parsed.get("overview") or "_Synthesis failed — model returned unparsable output._"),
        "key_papers": str(parsed.get("key_papers") or "_Synthesis failed._"),
        "themes": str(parsed.get("themes") or "_Synthesis failed._"),
        "gaps": str(parsed.get("gaps") or "_Synthesis failed._"),
        "future": str(parsed.get("future") or "_Synthesis failed._"),
        "references": references_md,
    }

    if coverage < COVERAGE_THRESHOLD:
        sections["overview"] = (
            f"_Caveat: evidence coverage reached only {coverage}% after {state.get('rounds', 0)} rounds._ "
            + sections["overview"]
        )

    return {**state, "sections": sections, "events": events}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("decompose", _decompose_node)
    g.add_node("search", _search_node)
    g.add_node("evaluate", _evaluate_node)
    g.add_node("synthesize", _synthesize_node)

    g.set_entry_point("decompose")
    g.add_edge("decompose", "search")
    g.add_edge("search", "evaluate")
    g.add_conditional_edges(
        "evaluate",
        _route_after_eval,
        {"decompose": "decompose", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", END)
    return g.compile()


_graph = build_graph()


# ---------------------------------------------------------------------------
# Public async generator
# ---------------------------------------------------------------------------

_SECTION_TITLES: dict[str, str] = {
    "overview": "Overview",
    "key_papers": "Key papers",
    "themes": "Emerging themes",
    "gaps": "Open challenges",
    "future": "Future directions",
    "references": "References",
}

_SECTION_ORDER: list[str] = ["overview", "key_papers", "themes", "gaps", "future", "references"]


async def run_research_agent(
    topic: str,
    user_email: str,
    search_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
) -> AsyncIterator[dict[str, Any]]:
    """Run the research graph and yield event dicts as work progresses."""

    initial: ResearchState = {
        "topic": topic,
        "user_email": user_email,
        "queries": [],
        "used_queries": [],
        "papers": [],
        "rounds": 0,
        "coverage": 0,
        "events": [],
        "sections": {},
        "search_fn": search_fn,
    }

    last_events_len = 0
    final_state: ResearchState = initial

    async for chunk in _graph.astream(initial, {"recursion_limit": 50}):
        # chunk is {node_name: updated_state_slice}
        for _node, node_state in chunk.items():
            final_state = {**final_state, **node_state}
            events = final_state.get("events", [])
            while last_events_len < len(events):
                yield events[last_events_len]
                last_events_len += 1

    sections = final_state.get("sections", {})
    for sid in _SECTION_ORDER:
        content = sections.get(sid, "")
        if not content:
            continue
        yield {
            "event": "section",
            "id": sid,
            "title": _SECTION_TITLES[sid],
            "content": content,
        }

    yield {
        "event": "done",
        "total_papers": len(final_state.get("papers", [])),
        "coverage": int(final_state.get("coverage", 0)),
    }
