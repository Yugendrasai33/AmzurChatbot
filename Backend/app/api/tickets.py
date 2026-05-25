import logging
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.tickets import (
    TicketCreateRequest,
    TicketCreateResponse,
    TicketListItem,
    TicketStatusUpdate,
)
from app.services.auth_service import AuthenticatedUser
from app.services.ticket_service import (
    create_ticket_via_n8n,
    get_ticket_by_id,
    get_user_tickets,
)

logger = logging.getLogger("tickets")

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Simple in-memory rate limiter: max 10 tickets per hour per user
_rate_limit: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


def _check_rate_limit(user_email: str) -> None:
    now = time.time()
    timestamps = _rate_limit[user_email]
    # Remove expired entries
    _rate_limit[user_email] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[user_email]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 tickets per hour.",
        )
    _rate_limit[user_email].append(now)


@router.post("/create", response_model=TicketCreateResponse)
async def create_ticket(
    request: TicketCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TicketCreateResponse:
    """Create a support ticket via n8n automation."""
    _check_rate_limit(current_user.email)

    try:
        result = await create_ticket_via_n8n(
            user_email=current_user.email,
            message=request.message,
            thread_id=request.thread_id,
        )
        return result
    except TimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("", response_model=list[TicketListItem])
async def list_tickets(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TicketListItem]:
    """List all tickets for the authenticated user."""
    return await get_user_tickets(db, current_user.email)


@router.get("/{ticket_id}", response_model=TicketListItem)
async def get_ticket(
    ticket_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TicketListItem:
    """Get a single ticket by ticket_id."""
    ticket = await get_ticket_by_id(db, ticket_id, current_user.email)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket
