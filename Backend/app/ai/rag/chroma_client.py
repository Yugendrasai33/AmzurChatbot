from __future__ import annotations

import functools

import chromadb

from app.core.config import settings


@functools.lru_cache(maxsize=1)
def _get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_user_collection(user_id: str) -> chromadb.Collection:
    """Return (or create) the per-user ChromaDB collection."""
    client = _get_client()
    return client.get_or_create_collection(name=f"user_{user_id}")
