from __future__ import annotations

import uuid
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.llm import embeddings
from app.ai.rag.chroma_client import get_user_collection

_SKIP_CATEGORIES = {"video", "image", "generated_image"}

_MIME_LOADER_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    "application/vnd.ms-excel": "excel",
}

_TEXT_MIMES: set[str] = {
    "text/plain",
    "text/x-python",
    "text/javascript",
    "text/html",
    "text/css",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def _resolve_loader(file_path: str, mime_type: str | None):
    loader_type = _MIME_LOADER_MAP.get(mime_type or "")
    if loader_type == "pdf":
        return PyPDFLoader(file_path)
    if loader_type == "excel":
        return UnstructuredExcelLoader(file_path)
    # Everything else (code, txt, markdown, csv, docx) → TextLoader
    return TextLoader(file_path, encoding="utf-8")


async def ingest_file(
    file_path: str,
    attachment_id: str,
    user_id: str,
    mime_type: str | None = None,
    type_category: str | None = None,
    filename: str | None = None,
) -> int:
    """Load, split, embed, and store a file in the user's ChromaDB collection.

    Returns the number of chunks ingested (0 for skipped file types).
    """
    if type_category in _SKIP_CATEGORIES:
        return 0

    resolved = Path(file_path)
    if not resolved.exists():
        return 0

    loader = _resolve_loader(str(resolved), mime_type)
    documents = loader.load()

    if not documents:
        return 0

    chunks = _splitter.split_documents(documents)
    if not chunks:
        return 0

    texts = [chunk.page_content for chunk in chunks]
    vectors = await embeddings.aembed_documents(texts)

    collection = get_user_collection(user_id)

    ids = [f"{attachment_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "attachment_id": attachment_id,
            "user_id": user_id,
            "file_path": str(resolved),
            "filename": filename or resolved.name,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )

    return len(chunks)
