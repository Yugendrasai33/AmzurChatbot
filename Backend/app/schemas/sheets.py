from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SheetsQueryRequest(BaseModel):
    """Request body for natural-language questions about spreadsheet data."""
    thread_id: UUID
    question: str
    source_type: str  # "csv" | "xlsx" | "google_sheet"
    sheet_url: Optional[str] = None
    attachment_id: Optional[str] = None


class SheetsQueryResponse(BaseModel):
    answer: str
    rows: int
    columns: list[str]
    thread_id: UUID


class CacheEntryInfo(BaseModel):
    key: str
    source_type: str
    cached_at: Optional[str] = None
    modified_time: Optional[str] = None
    rows: int
    columns: list[str]


class CacheStatusResponse(BaseModel):
    entries: list[CacheEntryInfo]
    total: int


class ClearCacheResponse(BaseModel):
    cleared: bool
    sheet_id: Optional[str] = None
    count: Optional[int] = None
