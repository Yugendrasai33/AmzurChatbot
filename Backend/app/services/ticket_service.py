import logging
import httpx
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.tickets import TicketCreateResponse, TicketListItem

logger = logging.getLogger("tickets")


def sanitize_message(message: str) -> str:
    """Sanitize user input before forwarding to n8n."""
    # Strip leading/trailing whitespace
    message = message.strip()
    # Remove any null bytes
    message = message.replace("\x00", "")
    # Limit length
    return message[:2000]


async def create_ticket_via_n8n(
    user_email: str,
    message: str,
    thread_id: Optional[str] = None,
) -> TicketCreateResponse:
    """Forward ticket creation request to n8n webhook and return structured response."""
    if not settings.N8N_WEBHOOK_URL:
        raise ValueError("N8N_WEBHOOK_URL is not configured")
    if not settings.N8N_API_KEY:
        raise ValueError("N8N_API_KEY is not configured")

    sanitized_message = sanitize_message(message)

    payload = {
        "email": user_email,
        "user_email": user_email,
        "source": "ai_forge_chatbot",
        "message": sanitized_message,
        "thread_id": thread_id or "",
    }

    headers = {
        "Content-Type": "application/json",
        "x-n8n-api-key": settings.N8N_API_KEY,
    }

    logger.info(f"Sending ticket request to n8n for user={user_email}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                settings.N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
            )
        except httpx.TimeoutException:
            logger.error("n8n webhook timed out")
            raise TimeoutError("Request timed out. Your ticket may still be processing.")
        except httpx.ConnectError:
            logger.error("n8n webhook unreachable")
            raise ConnectionError("Automation service is temporarily unavailable. Please try again later.")

    logger.info(f"n8n response status: {response.status_code}")
    logger.info(f"n8n response body: {response.text[:1000]}")

    if response.status_code == 404:
        logger.error("n8n webhook returned 404 — workflow may not be active or URL is incorrect")
        raise RuntimeError(
            "Automation service is not available. Please ensure the n8n workflow is active."
        )

    if response.status_code >= 500:
        logger.error(f"n8n returned server error: {response.status_code}")
        raise RuntimeError("Ticket creation failed. The automation service encountered an error.")

    if response.status_code not in (200, 201):
        logger.error(f"n8n returned unexpected status: {response.status_code} - {response.text[:500]}")
        raise RuntimeError(f"Ticket creation failed (status {response.status_code}). Please try again.")

    # Check if response is JSON
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        # Try parsing anyway — some n8n responses don't set content-type correctly
        pass

    try:
        raw = response.json()
    except Exception:
        logger.error(f"n8n returned non-JSON response: {response.text[:500]}")
        raise RuntimeError("Ticket creation failed. Received invalid response from automation service.")

    # n8n may return an array with a single object or a direct object
    if isinstance(raw, list):
        data = raw[0] if raw else {}
    else:
        data = raw

    logger.info(f"Parsed n8n data: {data}")

    # Accept response if it has a ticket_id (regardless of success flag)
    if not isinstance(data, dict) or (not data.get("success") and not data.get("ticket_id")):
        logger.error(f"n8n returned unsuccessful response: {data}")
        raise RuntimeError("Ticket creation failed. Please try again.")

    logger.info(f"Ticket created successfully: {data.get('ticket_id')}")

    return TicketCreateResponse(
        success=data.get("success", True),
        ticket_id=data.get("ticket_id", ""),
        category=data.get("category", "General"),
        priority=data.get("priority", "medium"),
        assigned_team=data.get("assigned_team", ""),
        status=data.get("status", "open"),
        summary=data.get("summary", f"Created {data.get('ticket_id', '')} | {data.get('category', 'General')} | {data.get('priority', 'medium')}"),
    )


async def get_user_tickets(db: AsyncSession, user_email: str) -> list[TicketListItem]:
    """Fetch all tickets for a given user from Supabase/PostgreSQL."""
    result = await db.execute(
        text(
            "SELECT id, ticket_id, user_email, issue, category, priority, status, "
            "assigned_team, created_at, updated_at, thread_id, next_action "
            "FROM public.tickets WHERE user_email = :email ORDER BY created_at DESC"
        ),
        {"email": user_email},
    )
    rows = result.mappings().all()
    return [
        TicketListItem(
            id=str(row["id"]),
            ticket_id=row["ticket_id"],
            user_email=row["user_email"],
            issue=row["issue"],
            category=row["category"],
            priority=row["priority"],
            status=row["status"],
            assigned_team=row.get("assigned_team"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            thread_id=row.get("thread_id"),
            next_action=row.get("next_action"),
        )
        for row in rows
    ]


async def get_ticket_by_id(
    db: AsyncSession, ticket_id: str, user_email: str
) -> Optional[TicketListItem]:
    """Fetch a single ticket by ticket_id, enforcing user isolation."""
    result = await db.execute(
        text(
            "SELECT id, ticket_id, user_email, issue, category, priority, status, "
            "assigned_team, created_at, updated_at, thread_id, next_action "
            "FROM public.tickets WHERE ticket_id = :ticket_id AND user_email = :email"
        ),
        {"ticket_id": ticket_id, "email": user_email},
    )
    row = result.mappings().first()
    if not row:
        return None
    return TicketListItem(
        id=str(row["id"]),
        ticket_id=row["ticket_id"],
        user_email=row["user_email"],
        issue=row["issue"],
        category=row["category"],
        priority=row["priority"],
        status=row["status"],
        assigned_team=row.get("assigned_team"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        thread_id=row.get("thread_id"),
        next_action=row.get("next_action"),
    )
