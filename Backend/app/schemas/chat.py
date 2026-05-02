from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
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


class ChatSendResponse(BaseModel):
    thread: ThreadResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    model: str
