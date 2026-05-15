from pydantic import BaseModel


class AttachmentMeta(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    type_category: str
    url: str


class UploadResponse(AttachmentMeta):
    pass
