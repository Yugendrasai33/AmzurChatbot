from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SectionId = Literal[
    "overview",
    "key_papers",
    "themes",
    "gaps",
    "future",
    "references",
    "error",
]


class ResearchRequest(BaseModel):
    """Request body for a research-digest stream."""

    thread_id: UUID
    topic: str = Field(..., min_length=3, max_length=500)

    @field_validator("topic")
    @classmethod
    def _clean_topic(cls, v: str) -> str:
        # Strip control chars and surrounding whitespace.
        cleaned = "".join(ch for ch in v if ch >= " " or ch == "\n").strip()
        if not cleaned:
            raise ValueError("topic must not be empty")
        return cleaned


class StatusEvent(BaseModel):
    event: Literal["status"] = "status"
    message: str


class SectionEvent(BaseModel):
    event: Literal["section"] = "section"
    id: SectionId
    title: str
    content: str


class DoneEvent(BaseModel):
    event: Literal["done"] = "done"
    total_papers: int
    coverage: int


ResearchEvent = Annotated[
    Union[StatusEvent, SectionEvent, DoneEvent],
    Field(discriminator="event"),
]


class ResearchSection(BaseModel):
    id: SectionId
    title: str
    content: str


class ResearchResponse(BaseModel):
    """Non-stream response shape (kept for OpenAPI docs / non-stream callers)."""

    topic: str
    sections: list[ResearchSection]
    total_papers: int
    coverage: int
    thread_id: UUID
