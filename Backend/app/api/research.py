from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.research import ResearchRequest
from app.services.auth_service import AuthenticatedUser
from app.services.research_service import stream_research_response

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/query")
async def research_query(
    request: ResearchRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream a structured research digest for a TOPIC over SSE."""

    async def event_generator():
        try:
            async for payload in stream_research_response(
                topic=request.topic,
                thread_id=request.thread_id,
                user_id=UUID(current_user.id),
                user_email=current_user.email,
                db=db,
            ):
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except OpenAIError as e:
            yield f"data: [ERROR] LLM service unavailable: {e}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
