from __future__ import annotations

import base64
import io
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import client, llm
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.chat_message import ChatMessage, ChatThread
from app.services.attachment_service import (
    detect_mime,
    format_attachment_meta,
    get_attachment,
    get_file_path,
    save_upload,
)


class _NamedBytesIO(io.BytesIO):
    """BytesIO with a name attribute required by the OpenAI SDK file upload."""
    def __init__(self, content: bytes, name: str) -> None:
        super().__init__(content)
        self.name = name


def _validate_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_prompt", "message": "Prompt cannot be empty."},
        )
    if len(cleaned) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_prompt", "message": "Prompt must be at least 10 characters."},
        )
    if len(cleaned) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_prompt", "message": "Prompt must be at most 1000 characters."},
        )
    return cleaned


async def _resolve_thread(db: AsyncSession, user_id: str, prompt: str, thread_id: str | None) -> ChatThread:
    if thread_id:
        existing = (
            await db.execute(
                select(ChatThread).where(
                    ChatThread.id == uuid.UUID(thread_id),
                    ChatThread.user_id == uuid.UUID(user_id),
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    title = f"Image: {prompt[:40].strip()}" or "Image chat"
    thread = ChatThread(user_id=uuid.UUID(user_id), title=title)
    db.add(thread)
    await db.flush()
    return thread


def _extract_image_url_or_b64(image_response: object) -> tuple[str | None, str | None]:
    data = getattr(image_response, "data", None)
    if not data:
        return None, None
    first = data[0]
    url = getattr(first, "url", None)
    b64_json = getattr(first, "b64_json", None)
    return url, b64_json


async def _download_or_decode_image(url: str | None, b64_json: str | None) -> bytes:
    if b64_json:
        return base64.b64decode(b64_json)

    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "image_generation_failed", "message": "No image payload received from model."},
        )

    async with httpx.AsyncClient(timeout=60) as http_client:
        response = await http_client.get(url)
        response.raise_for_status()
        return response.content


async def generate_image_from_prompt(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    prompt: str,
    thread_id: str | None = None,
) -> dict:
    """Generate an image via LiteLLM proxy and persist it as an attachment on an assistant message."""
    if not settings.IMAGE_GEN_MODEL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "config_error", "message": "IMAGE_GEN_MODEL is not configured."},
        )

    cleaned_prompt = _validate_prompt(prompt)
    thread = await _resolve_thread(db, user_id, cleaned_prompt, thread_id)

    user_message = ChatMessage(
        thread_id=thread.id,
        user_id=uuid.UUID(user_id),
        role="user",
        content=f"/image {cleaned_prompt}",
    )
    db.add(user_message)
    await db.flush()

    try:
        image_response = client.with_options(timeout=60).images.generate(
            model=settings.IMAGE_GEN_MODEL,
            prompt=cleaned_prompt,
            user=user_email,
            extra_body={
                "metadata": {
                    "application": settings.APP_NAME,
                    "environment": settings.ENVIRONMENT,
                }
            },
        )
        url, b64_json = _extract_image_url_or_b64(image_response)
        image_bytes = await _download_or_decode_image(url, b64_json)
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "llm_error", "message": str(exc)},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unexpected", "message": str(exc)},
        ) from exc

    detected_mime = detect_mime(image_bytes, filename="generated.png", content_type="image/png")
    attachment = await save_upload(
        db=db,
        user_id=user_id,
        filename="generated-image.png",
        file_bytes=image_bytes,
        detected_mime=detected_mime,
        type_category="generated_image",
    )

    assistant_message = ChatMessage(
        thread_id=thread.id,
        user_id=uuid.UUID(user_id),
        role="assistant",
        content=f"Generated image for: {cleaned_prompt}",
        model=settings.IMAGE_GEN_MODEL,
    )
    db.add(assistant_message)
    await db.flush()

    attachment.message_id = assistant_message.id
    thread.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(attachment)

    return format_attachment_meta(attachment)


_EDIT_SYSTEM_PROMPT = (
    "You are editing a previously generated image.\n\n"
    "New User Modification: {edit_prompt}\n\n"
    "Instruction:\n"
    "Edit the previously generated image using this new modification request while preserving:\n"
    "* style\n"
    "* composition\n"
    "* lighting\n"
    "* colors\n"
    "* camera angle\n"
    "* subject identity\n"
    "* background\n"
    "* overall aesthetic\n\n"
    "Do not create a new unrelated image. Preserve all major visual elements from the previous "
    "image unless explicitly changed by the add-on request.\n\n"
    "If any requested change conflicts with the original image, prioritize preserving the original "
    "image and apply the smallest necessary adjustment.\n\n"
    "Generate a high-quality updated version with the exact same aspect ratio and visual consistency "
    "as the original image."
)

_DESCRIBE_IMAGE_PROMPT = (
    "Describe this image in rich detail for an image generation model. "
    "Include: subject, pose, composition, lighting, colors, background, art style, mood, "
    "camera angle, textures. Be precise and vivid. Do NOT include any commentary — "
    "only the image description, as one continuous paragraph."
)


async def _describe_image_via_vision(image_bytes: bytes, mime_type: str) -> str:
    """Use the Gemini vision model to describe the image for re-generation."""
    from langchain_core.messages import HumanMessage

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    message = HumanMessage(
        content=[
            {"type": "text", "text": _DESCRIBE_IMAGE_PROMPT},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            },
        ]
    )
    response = await llm.ainvoke([message])
    return response.content.strip() if isinstance(response.content, str) else str(response.content).strip()


async def edit_image_from_prompt(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    attachment_id: str,
    edit_prompt: str,
    thread_id: str | None = None,
) -> dict:
    """Edit an existing generated image by describing it, then re-generating with modifications."""
    if not settings.IMAGE_GEN_MODEL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "config_error", "message": "IMAGE_GEN_MODEL is not configured."},
        )

    cleaned_edit = _validate_prompt(edit_prompt)

    # Load original image from disk
    original = await get_attachment(db, attachment_id, user_id)
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Original attachment not found."},
        )
    original_path = get_file_path(original)
    if not original_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Original image file not found on disk."},
        )
    image_bytes = original_path.read_bytes()

    # Resolve (or reuse) thread
    resolved_thread = await _resolve_thread(db, user_id, cleaned_edit, thread_id)

    user_message = ChatMessage(
        thread_id=resolved_thread.id,
        user_id=uuid.UUID(user_id),
        role="user",
        content=f"/edit-image {cleaned_edit}",
    )
    db.add(user_message)
    await db.flush()

    try:
        # Step 1: Describe the original image using Gemini vision
        mime = original.mime_type or "image/png"
        description = await _describe_image_via_vision(image_bytes, mime)

        # Step 2: Build combined prompt and generate new image
        combined_prompt = (
            f"Original image description: {description}\n\n"
            f"Modification requested: {cleaned_edit}\n\n"
            f"Generate an image that matches the original description above but with "
            f"the requested modification applied. Keep everything else identical — same style, "
            f"composition, lighting, colors, camera angle, background, and overall aesthetic. "
            f"Only change what the modification explicitly asks for."
        )

        image_response = client.with_options(timeout=90).images.generate(
            model=settings.IMAGE_GEN_MODEL,
            prompt=combined_prompt,
            user=user_email,
            extra_body={
                "metadata": {
                    "application": settings.APP_NAME,
                    "environment": settings.ENVIRONMENT,
                }
            },
        )
        url, b64_json = _extract_image_url_or_b64(image_response)
        edited_bytes = await _download_or_decode_image(url, b64_json)
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "llm_error", "message": str(exc)},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unexpected", "message": str(exc)},
        ) from exc

    detected_mime = detect_mime(edited_bytes, filename="edited.png", content_type="image/png")
    attachment = await save_upload(
        db=db,
        user_id=user_id,
        filename="edited-image.png",
        file_bytes=edited_bytes,
        detected_mime=detected_mime,
        type_category="generated_image",
    )

    assistant_message = ChatMessage(
        thread_id=resolved_thread.id,
        user_id=uuid.UUID(user_id),
        role="assistant",
        content=f"Edited image: {cleaned_edit}",
        model=settings.IMAGE_GEN_MODEL,
    )
    db.add(assistant_message)
    await db.flush()

    attachment.message_id = assistant_message.id
    resolved_thread.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(attachment)

    return format_attachment_meta(attachment)
