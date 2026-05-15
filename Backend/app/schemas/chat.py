from pydantic import BaseModel

from app.schemas.attachment import AttachmentMeta


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    attachment_ids: list[str] | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str
    thread_id: str | None = None


class ImageEditRequest(BaseModel):
    attachment_id: str
    edit_prompt: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    model: str


class ThreadCreateRequest(BaseModel):
    title: str | None = None


class ThreadUpdateRequest(BaseModel):
    title: str


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    model: str | None = None
    created_at: str
    attachments: list[AttachmentMeta] | None = None


class ChatSendResponse(BaseModel):
    thread: ThreadResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    model: str
