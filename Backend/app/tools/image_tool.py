"""Image generation tool — wraps existing image generation via OpenAI client."""
from __future__ import annotations

from typing import Any


async def execute_image_generation(prompt: str, user_email: str = "system") -> dict[str, Any]:
    """Generate an image from a text prompt.

    Args:
        prompt: Text description of the image to generate
        user_email: User's email for LLM metadata

    Returns:
        dict with keys: success, message (confirmation only — actual images
        are handled by the full service pipeline with attachment storage)
    """
    if not prompt or not prompt.strip():
        return {"success": False, "error": "Prompt cannot be empty"}

    if len(prompt.strip()) < 10:
        return {"success": False, "error": "Prompt must be at least 10 characters"}

    if len(prompt.strip()) > 1000:
        return {"success": False, "error": "Prompt must be at most 1000 characters"}

    try:
        from app.ai.llm import client
        from app.core.config import settings

        if not settings.IMAGE_GEN_MODEL:
            return {"success": False, "error": "IMAGE_GEN_MODEL is not configured"}

        # Generate the image
        image_response = client.with_options(timeout=60).images.generate(
            model=settings.IMAGE_GEN_MODEL,
            prompt=prompt.strip(),
            user=user_email,
            extra_body={
                "metadata": {
                    "application": settings.APP_NAME,
                    "environment": settings.ENVIRONMENT,
                }
            },
        )

        # Check if we got a response
        data = getattr(image_response, "data", None)
        if not data:
            return {"success": False, "error": "No image data received from model"}

        first = data[0]
        has_url = bool(getattr(first, "url", None))
        has_b64 = bool(getattr(first, "b64_json", None))

        return {
            "success": True,
            "message": "Image generated successfully",
            "has_url": has_url,
            "has_b64": has_b64,
            "prompt": prompt.strip(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Image generation failed: {e}",
        }
