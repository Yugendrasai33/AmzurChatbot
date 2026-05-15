from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
import re

from app.ai.llm import embeddings
from app.ai.rag.chroma_client import get_user_collection

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.",
    re.IGNORECASE,
)


class RetrievalResult:
    """Holds retrieved chunk texts and their source filenames."""

    def __init__(self, texts: list[str], sources: list[str], unresolved_attachment_ids: list[str] | None = None):
        self.texts = texts
        self.sources = sources
        # Attachment IDs whose original filename could not be determined from metadata
        self.unresolved_attachment_ids = unresolved_attachment_ids or []


async def retrieve_context(
    query: str,
    user_id: str,
    k: int = 4,
    attachment_ids: list[str] | None = None,
) -> RetrievalResult:
    """Embed *query* and return the top-k matching chunk texts with source filenames.

    If *attachment_ids* is provided, only chunks belonging to those attachments are
    searched.  Returns an empty RetrievalResult when the collection is missing or
    empty — never raises.
    """
    try:
        collection = get_user_collection(user_id)
        if collection.count() == 0:
            return RetrievalResult([], [])

        query_vector = await embeddings.aembed_query(query)

        # Build optional where filter to scope by attachment_ids
        where_filter = None
        if attachment_ids:
            if len(attachment_ids) == 1:
                where_filter = {"attachment_id": attachment_ids[0]}
            else:
                where_filter = {"attachment_id": {"$in": attachment_ids}}

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas"],
            where=where_filter,
        )

        documents = results.get("documents")
        metadatas = results.get("metadatas")
        if not documents or not documents[0]:
            return RetrievalResult([], [])

        texts = documents[0]
        # Extract unique source filenames preserving order
        sources: list[str] = []
        unresolved_ids: list[str] = []
        if metadatas and metadatas[0]:
            for meta in metadatas[0]:
                fname = meta.get("filename") or ""
                # Fallback: derive from file_path if filename wasn't stored
                if not fname or fname == "Unknown":
                    fp = meta.get("file_path", "")
                    if fp:
                        fname = PureWindowsPath(fp).name or PurePosixPath(fp).name
                # Skip UUID-based filenames (stored name leaked into metadata)
                if fname and _UUID_PATTERN.match(fname):
                    aid = meta.get("attachment_id", "")
                    if aid and aid not in unresolved_ids:
                        unresolved_ids.append(aid)
                    fname = ""
                if fname and fname not in sources:
                    sources.append(fname)

        return RetrievalResult(texts, sources, unresolved_ids)
    except Exception:
        return RetrievalResult([], [])
