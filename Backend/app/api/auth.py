import base64
import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, SignupRequest
from app.services.auth_service import (
    AuthenticatedUser,
    auth_service,
    ensure_profile,
    get_profile,
    hash_password_for_profile,
)
from app.services.auth_service import find_profile_by_google_or_email, issue_local_jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


async def _try_ensure_profile(
    db: AsyncSession | None,
    user_id: str,
    email: str,
    full_name: str | None = None,
    password_hash: str | None = None,
    google_id: str | None = None,
    avatar_url: str | None = None,
    auth_provider: str | None = None,
) -> None:
    """Persist profile — silently skipped if DB is unavailable."""
    if db is None:
        return
    try:
        await ensure_profile(
            db, user_id, email, full_name, password_hash=password_hash,
            google_id=google_id, avatar_url=avatar_url, auth_provider=auth_provider,
        )
    except Exception as exc:
        logger.warning("Could not persist profile (DB unavailable): %s", exc)


async def _get_optional_db() -> AsyncSession | None:
    """Yields a DB session, or None when DB session factory is unavailable."""
    from app.db.session import SessionLocal
    if SessionLocal is None:
        yield None
        return
    async with SessionLocal() as session:
        yield session


@router.get("/google/login")
async def google_login(
    frontend_redirect: str = Query(default=f"{settings.FRONTEND_ORIGIN}/auth/google/callback"),
) -> RedirectResponse:
    return RedirectResponse(url=auth_service.build_google_auth_url(frontend_redirect))


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    db: Annotated[AsyncSession | None, Depends(_get_optional_db)] = None,
) -> RedirectResponse:
    frontend_redirect = f"{settings.FRONTEND_ORIGIN}/auth/google/callback"
    if state:
        try:
            frontend_redirect = base64.urlsafe_b64decode(state.encode("ascii")).decode("utf-8")
        except Exception:
            pass

    if not code:
        params = urlencode({"error": "Google OAuth callback missing code"})
        return RedirectResponse(url=f"{frontend_redirect}?{params}")

    try:
        # 1. Exchange code with Google and decode id_token – no Supabase needed.
        google_info = await auth_service.decode_google_user_from_code(code)
        google_id: str = google_info["google_id"]
        email: str = google_info["email"]
        full_name: str | None = google_info["full_name"]
        avatar_url: str | None = google_info["avatar_url"]

        if not email:
            raise HTTPException(status_code=400, detail="Google account has no email address")

        # 2. Validate employee email domain.
        auth_service._validate_employee_email(email)

        # 3. Find existing profile by google_id (most specific) or email.
        user_id: str | None = None
        if db is not None:
            profile = await find_profile_by_google_or_email(db, google_id, email)
            if profile:
                user_id = str(profile.id)

        # 4. If no profile found, create a new Supabase auth user (satisfies FK).
        if user_id is None:
            supabase_user = await auth_service.admin_create_google_user(email, full_name)
            user_id = supabase_user["id"]

        # 5. Upsert profile with Google fields.
        await _try_ensure_profile(
            db, user_id, email, full_name,
            google_id=google_id, avatar_url=avatar_url, auth_provider="google",
        )

        # 6. Issue a locally-signed JWT (works without Supabase Google provider).
        access_token = issue_local_jwt(user_id, email)

        params = urlencode(
            {
                "access_token": access_token,
                "refresh_token": "",
                "user_id": user_id,
                "email": email,
                "full_name": full_name or "",
            }
        )
        return RedirectResponse(url=f"{frontend_redirect}?{params}")
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        params = urlencode({"error": detail})
        return RedirectResponse(url=f"{frontend_redirect}?{params}")


@router.post("/signup", response_model=AuthResponse)
async def signup(
    request: SignupRequest,
    db: Annotated[AsyncSession | None, Depends(_get_optional_db)],
) -> AuthResponse:
    # Validate employee email domain first (raises 403 if not allowed)
    auth_service._validate_employee_email(request.email)

    # Use admin API to create user with auto-confirmed email (no verification email sent)
    user_data = await auth_service.admin_create_user(request.email, request.password, request.full_name)
    user_id = user_data["id"]
    user_email = user_data["email"]

    # Login immediately to get a session token
    session_data = await auth_service.login(request.email, request.password)

    password_hash = hash_password_for_profile(request.password)
    await _try_ensure_profile(
        db,
        user_id,
        user_email,
        request.full_name,
        password_hash=password_hash,
    )

    return AuthResponse(
        access_token=session_data["access_token"],
        refresh_token=session_data["refresh_token"],
        user=AuthUser(id=user_id, email=user_email, full_name=request.full_name),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession | None, Depends(_get_optional_db)],
) -> AuthResponse:
    payload = await auth_service.login(request.email, request.password)
    user = payload["user"]
    full_name = user.get("user_metadata", {}).get("full_name")

    await _try_ensure_profile(db, user["id"], user["email"], full_name)

    return AuthResponse(
        access_token=payload["access_token"],
        refresh_token=payload["refresh_token"],
        user=AuthUser(id=user["id"], email=user["email"], full_name=full_name),
    )


@router.get("/me", response_model=AuthUser)
async def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession | None, Depends(_get_optional_db)],
) -> AuthUser:
    full_name = None
    avatar_url = None
    if db is not None:
        try:
            profile = await get_profile(db, current_user.id)
            full_name = profile.full_name if profile else None
            avatar_url = profile.avatar_url if profile else None
        except Exception as exc:
            logger.warning("Could not fetch profile: %s", exc)
    return AuthUser(id=current_user.id, email=current_user.email, full_name=full_name, avatar_url=avatar_url)
