from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.rag import IngestResponse, RagQueryRequest
from app.services.auth_service import AuthenticatedUser
from app.services.rag_service import ingest_attachment, stream_rag_response

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/ingest/{attachment_id}", response_model=IngestResponse)
async def ingest(
    attachment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IngestResponse:
    try:
        return await ingest_attachment(attachment_id, current_user.id, db)
    except HTTPException:
        raise
    except OpenAIError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": "llm_error", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "unexpected", "message": str(e)},
        )


@router.post("/stream")
async def rag_stream(
    request: RagQueryRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    async def event_generator():
        try:
            async for token in stream_rag_response(
                message=request.message,
                thread_id=request.thread_id,
                user_id=UUID(current_user.id),
                user_email=current_user.email,
                db=db,
                attachment_ids=request.attachment_ids,
            ):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except OpenAIError as e:
            yield f"data: [ERROR] LLM service unavailable: {e}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
