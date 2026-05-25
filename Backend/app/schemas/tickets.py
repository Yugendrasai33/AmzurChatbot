from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TicketCreateRequest(BaseModel):
    message: str = Field(..., min_length=10, max_length=2000)
    thread_id: Optional[str] = None


class TicketCreateResponse(BaseModel):
    success: bool
    ticket_id: str
    category: str
    priority: str
    assigned_team: str
    status: str
    summary: str


class TicketListItem(BaseModel):
    id: str
    ticket_id: str
    user_email: str
    issue: str
    category: str
    priority: str
    status: str
    assigned_team: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    thread_id: Optional[str] = None
    next_action: Optional[str] = None


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(open|in_progress|resolved|closed)$")
