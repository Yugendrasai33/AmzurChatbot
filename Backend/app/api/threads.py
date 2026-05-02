from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.chat import ChatMessageResponse, ThreadCreateRequest, ThreadResponse, ThreadUpdateRequest
from app.services.auth_service import AuthenticatedUser
from app.services.chat_service import create_thread, delete_thread, get_thread_messages, list_threads, rename_thread

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.get("", response_model=list[ThreadResponse])
async def get_threads(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ThreadResponse]:
    rows = await list_threads(db, current_user.id)
    return [ThreadResponse(**row) for row in rows]


@router.post("", response_model=ThreadResponse)
async def new_thread(
    request: ThreadCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    row = await create_thread(db, current_user.id, request.title)
    return ThreadResponse(**row)


@router.put("/{thread_id}", response_model=ThreadResponse)
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


@router.delete("/{thread_id}")
async def remove_thread(
    thread_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    deleted = await delete_thread(db, current_user.id, thread_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return {"deleted": True}


@router.get("/{thread_id}/messages", response_model=list[ChatMessageResponse])
async def thread_messages(
    thread_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChatMessageResponse]:
    rows = await get_thread_messages(db, current_user.id, thread_id)
    return [ChatMessageResponse(**row) for row in rows]
