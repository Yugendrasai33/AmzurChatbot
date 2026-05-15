from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.attachment import AttachmentMeta
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSendResponse,
    ImageEditRequest,
    ImageGenerationRequest,
    ThreadCreateRequest,
    ThreadUpdateRequest,
    ThreadResponse,
)
from app.services.attachment_service import (
    classify_mime,
    detect_mime,
    format_attachment_meta,
    get_attachment,
    get_file_path,
    save_upload,
)
from app.services.auth_service import AuthenticatedUser
from app.services.image_service import edit_image_from_prompt, generate_image_from_prompt
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
        attachment_ids=request.attachment_ids,
    )
    return ChatSendResponse(
        thread=ThreadResponse(**payload["thread"]),
        user_message=ChatMessageResponse(**payload["user_message"]),
        assistant_message=ChatMessageResponse(**payload["assistant_message"]),
        model=payload["model"],
    )


@router.post("/generate-image", response_model=AttachmentMeta)
async def generate_image(
    request: ImageGenerationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttachmentMeta:
    print(f"[DEBUG] Image generation request: user={current_user.id}, prompt={request.prompt}")
    try:
        data = await generate_image_from_prompt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            prompt=request.prompt,
            thread_id=request.thread_id,
        )
        print(f"[DEBUG] Image generation succeeded: {data}")
        return AttachmentMeta(**data)
    except Exception as exc:
        print(f"[DEBUG] Image generation failed: {exc}")
        raise


@router.post("/edit-image", response_model=AttachmentMeta)
async def edit_image(
    request: ImageEditRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttachmentMeta:
    data = await edit_image_from_prompt(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        attachment_id=request.attachment_id,
        edit_prompt=request.edit_prompt,
        thread_id=request.thread_id,
    )
    return AttachmentMeta(**data)


@router.post("/upload", response_model=AttachmentMeta)
async def upload_file(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> AttachmentMeta:
    """Upload a file attachment."""
    # Read file bytes
    file_bytes = await file.read()

    # Enforce size limit
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "file_too_large", "message": f"File exceeds {settings.MAX_UPLOAD_MB}MB limit"},
        )

    # Detect MIME type server-side
    detected_mime = detect_mime(file_bytes, filename=file.filename, content_type=file.content_type)
    type_category = classify_mime(detected_mime)

    if type_category is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "unsupported_type", "message": f"File type '{detected_mime}' is not allowed"},
        )

    filename = file.filename or "unnamed"
    attachment = await save_upload(db, current_user.id, filename, file_bytes, detected_mime, type_category)
    await db.commit()
    await db.refresh(attachment)

    return AttachmentMeta(**format_attachment_meta(attachment))


@router.get("/uploads/{file_id}")
async def serve_upload(
    file_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """Serve an uploaded file (only to owner)."""
    attachment = await get_attachment(db, file_id, current_user.id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = get_file_path(attachment)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=attachment.mime_type,
        filename=attachment.filename,
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
