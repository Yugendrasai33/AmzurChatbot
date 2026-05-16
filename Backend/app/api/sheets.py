from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.sheets import (
    CacheStatusResponse,
    ClearCacheResponse,
    SheetsQueryRequest,
)
from app.services.auth_service import AuthenticatedUser
from app.services.sheets_query_service import stream_sheets_response
from app.services.sheets_service import clear_sheet_cache, get_cache_status

router = APIRouter(prefix="/api/sheets", tags=["sheets"])


@router.post("/query")
async def sheets_query(
    request: SheetsQueryRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh: bool = Query(False, description="Force re-fetch sheet data, bypassing cache"),
) -> StreamingResponse:
    # Track cache status via a mutable container
    cache_status_holder = {"value": "MISS"}

    async def event_generator():
        try:
            async for token in stream_sheets_response(
                question=request.question,
                thread_id=request.thread_id,
                user_id=UUID(current_user.id),
                user_email=current_user.email,
                source_type=request.source_type,
                db=db,
                sheet_url=request.sheet_url,
                attachment_id=request.attachment_id,
                refresh=refresh,
            ):
                # Extract cache status from SHEET_META if present
                if "[SHEET_META]" in token:
                    import json as _json
                    try:
                        meta_json = token.split("[SHEET_META]")[1]
                        meta = _json.loads(meta_json)
                        cache_status_holder["value"] = meta.get("cache_status", "MISS")
                    except Exception:
                        pass
                    yield f"data: {token}\n\n"
                else:
                    # Split multi-line answers (e.g. markdown tables) into
                    # separate SSE data events so the frontend reader can
                    # process each line individually.
                    lines = token.split("\n")
                    for line in lines:
                        yield f"data: {line}\n\n"
            yield "data: [DONE]\n\n"
        except OpenAIError as e:
            yield f"data: [ERROR] LLM service unavailable: {e}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
            yield "data: [DONE]\n\n"

    # Determine X-Cache header value
    x_cache = "FORCED-MISS" if refresh else "MISS"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Cache": x_cache},
    )


@router.get("/cache/status", response_model=CacheStatusResponse)
async def cache_status(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CacheStatusResponse:
    """Return info about all current cache entries."""
    entries = get_cache_status()
    return CacheStatusResponse(entries=entries, total=len(entries))


@router.delete("/cache/{sheet_id}", response_model=ClearCacheResponse)
async def clear_single_cache(
    sheet_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ClearCacheResponse:
    """Clear cache for a specific sheet_id."""
    count = clear_sheet_cache(sheet_id)
    return ClearCacheResponse(cleared=count > 0, sheet_id=sheet_id, count=count)


@router.delete("/cache", response_model=ClearCacheResponse)
async def clear_all_cache(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ClearCacheResponse:
    """Clear ALL cached DataFrames."""
    count = clear_sheet_cache()
    return ClearCacheResponse(cleared=True, count=count)
