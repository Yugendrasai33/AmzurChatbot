from uuid import UUID

from pydantic import BaseModel


class SqlQueryRequest(BaseModel):
    thread_id: UUID
    question: str


class SqlQueryResponse(BaseModel):
    answer: str
    sql_query: str
    thread_id: UUID
