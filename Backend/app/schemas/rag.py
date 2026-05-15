from uuid import UUID

from pydantic import BaseModel


class IngestResponse(BaseModel):
    attachment_id: str
    chunks_ingested: int


class RagQueryRequest(BaseModel):
    thread_id: UUID
    message: str
    attachment_ids: list[str] | None = None
