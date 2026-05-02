from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSendResponse,
    ThreadCreateRequest,
    ThreadUpdateRequest,
    ThreadResponse,
)
from app.services.auth_service import AuthenticatedUser
from app.services.chat_service import (
    create_thread,
    delete_thread,
    get_chat_response,
    get_thread_messages,
    list_threads,
    rename_thread,
    send_message_with_persistence,
    stream_chat_response,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/threads", response_model=list[ThreadResponse])
async def get_threads(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ThreadResponse]:
    rows = await list_threads(db, current_user.id)
    return [ThreadResponse(**row) for row in rows]


@router.post("/threads", response_model=ThreadResponse)
async def new_thread(
    request: ThreadCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    row = await create_thread(db, current_user.id, request.title)
    return ThreadResponse(**row)


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    request: ThreadUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    row = await rename_thread(db, current_user.id, thread_id, request.title)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return ThreadResponse(**row)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread_put(
    thread_id: str,
    request: ThreadUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    row = await rename_thread(db, current_user.id, thread_id, request.title)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return ThreadResponse(**row)


@router.delete("/threads/{thread_id}")
async def remove_thread(
    thread_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    deleted = await delete_thread(db, current_user.id, thread_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return {"deleted": True}


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
async def thread_messages(
    thread_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChatMessageResponse]:
    rows = await get_thread_messages(db, current_user.id, thread_id)
    return [ChatMessageResponse(**row) for row in rows]


@router.post("/messages", response_model=ChatSendResponse)
async def send_message(
    request: ChatRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSendResponse:
    payload = await send_message_with_persistence(
        db,
        current_user.id,
        request.message,
        request.thread_id,
    )
    return ChatSendResponse(
        thread=ThreadResponse(**payload["thread"]),
        user_message=ChatMessageResponse(**payload["user_message"]),
        assistant_message=ChatMessageResponse(**payload["assistant_message"]),
        model=payload["model"],
    )


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Compatibility endpoint for non-persistent chat usage."""
    response = await get_chat_response(request.message)
    return ChatResponse(response=response, model=settings.LLM_MODEL)


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Send a message and get a streaming response (SSE)."""

    async def event_generator():
        async for token in stream_chat_response(request.message):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
