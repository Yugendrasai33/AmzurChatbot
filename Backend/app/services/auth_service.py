import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import Profile


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password_for_profile(password: str) -> str:
    """Hash password for local profile storage using PBKDF2-SHA256."""
    salt = secrets.token_bytes(16)
    iterations = 390000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    hash_b64 = base64.urlsafe_b64encode(derived).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


_LOCAL_JWT_ISSUER = "amzur-ai-chat-local"


@dataclass
class AuthenticatedUser:
    id: str
    email: str


def issue_local_jwt(user_id: str, email: str) -> str:
    """Issue a locally-signed JWT for Google-authenticated users."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "iss": _LOCAL_JWT_ISSUER,
        "exp": expire,
    }
    return jose_jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_local_jwt(token: str) -> AuthenticatedUser:
    """Decode and validate a locally-signed JWT. Raises 401 on failure."""
    try:
        claims = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if claims.get("iss") != _LOCAL_JWT_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
        )

    try:
        return AuthenticatedUser(id=claims["sub"], email=claims["email"])
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload incomplete",
        ) from exc


async def find_profile_by_google_or_email(
    db: AsyncSession,
    google_id: str,
    email: str,
) -> Profile | None:
    """Look up a profile by google_id first, then fall back to email."""
    if google_id:
        result = await db.execute(select(Profile).where(Profile.google_id == google_id))
        profile = result.scalar_one_or_none()
        if profile:
            return profile

    result = await db.execute(select(Profile).where(Profile.email == _normalize_email(email)))
    return result.scalar_one_or_none()


async def ensure_profile(
    db: AsyncSession,
    user_id: str,
    email: str,
    full_name: str | None = None,
    password_hash: str | None = None,
    google_id: str | None = None,
    avatar_url: str | None = None,
    auth_provider: str | None = None,
) -> Profile:
    """Create or update a profile row. Optional fields are only written when provided."""
    profile_uuid = UUID(user_id)
    profile = await db.get(Profile, profile_uuid)

    if profile:
        changed = False
        if full_name is not None and profile.full_name != full_name:
            profile.full_name = full_name
            changed = True
        if password_hash is not None and profile.password_hash != password_hash:
            profile.password_hash = password_hash
            changed = True
        if google_id is not None and profile.google_id != google_id:
            profile.google_id = google_id
            changed = True
        if avatar_url is not None and profile.avatar_url != avatar_url:
            profile.avatar_url = avatar_url
            changed = True
        if auth_provider is not None and profile.auth_provider != auth_provider:
            profile.auth_provider = auth_provider
            changed = True
        if changed:
            await db.commit()
            await db.refresh(profile)
        return profile

    profile = Profile(
        id=profile_uuid,
        email=_normalize_email(email),
        full_name=full_name,
        password_hash=password_hash,
        google_id=google_id,
        avatar_url=avatar_url,
        auth_provider=auth_provider or ("google" if google_id else "email"),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_profile(db: AsyncSession, user_id: str) -> Profile | None:
    result = await db.execute(select(Profile).where(Profile.id == UUID(user_id)))
    return result.scalar_one_or_none()


class SupabaseAuthService:
    def __init__(self) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required.")

        self.auth_base = f"{settings.SUPABASE_URL}/auth/v1"
        self.api_key = settings.SUPABASE_ANON_KEY
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY or self.api_key
        self.admin_base = f"{settings.SUPABASE_URL}/auth/v1/admin"

    def _validate_employee_email(self, email: str) -> str:
        normalized = _normalize_email(email)

        if normalized.count("@") != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format.",
            )

        local_part, domain = normalized.split("@", maxsplit=1)
        if not local_part or not domain or domain.startswith(".") or domain.endswith("."):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format.",
            )

        allowed_domains = {
            part.strip().lower()
            for part in settings.EMPLOYEE_EMAIL_DOMAINS.split(",")
            if part.strip()
        }
        if domain not in allowed_domains:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employee email domains are allowed.",
            )

        return normalized

    def _headers(self, access_token: str | None = None) -> dict:
        bearer = access_token if access_token else self.api_key
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        }

    def _admin_headers(self) -> dict:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    def build_google_auth_url(self, frontend_redirect: str) -> str:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured.",
            )

        state = base64.urlsafe_b64encode(frontend_redirect.encode("utf-8")).decode("ascii")
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def _exchange_code_with_google(self, code: str) -> dict:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth credentials are not configured.",
            )

        token_payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data=token_payload)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google token exchange failed: {response.text}",
            )

        return response.json()

    @staticmethod
    def _decode_google_id_token(id_token: str) -> dict:
        try:
            claims: dict = jose_jwt.get_unverified_claims(id_token)
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not decode Google id_token",
            ) from exc

        issuer = claims.get("iss", "")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google token issuer",
            )

        return claims

    async def decode_google_user_from_code(self, code: str) -> dict:
        google_data = await self._exchange_code_with_google(code)
        id_token = google_data.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google did not return an id_token",
            )

        claims = self._decode_google_id_token(id_token)
        google_id = claims.get("sub", "")
        email = claims.get("email", "")
        full_name = claims.get("name")
        avatar_url = claims.get("picture")

        if not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token missing sub (user id)",
            )

        return {
            "google_id": google_id,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url,
        }

    async def _find_supabase_user_by_email(self, email: str) -> dict | None:
        url = f"{self.admin_base}/users"
        page = 1
        per_page = 50
        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                response = await client.get(
                    url,
                    params={"page": page, "per_page": per_page},
                    headers=self._admin_headers(),
                )
                if response.status_code >= 400:
                    break
                payload = response.json()
                users = payload.get("users", [])
                for user in users:
                    if user.get("email", "").lower() == email.lower():
                        return user
                if len(users) < per_page:
                    break
                page += 1
        return None

    async def admin_create_google_user(self, email: str, full_name: str | None) -> dict:
        url = f"{self.admin_base}/users"
        payload = {
            "email": email,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name, "provider": "google"},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=self._admin_headers())

        if response.status_code in (400, 422):
            existing = await self._find_supabase_user_by_email(email)
            if existing:
                return existing
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )

        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()

    async def signup(self, email: str, password: str, full_name: str | None = None) -> dict:
        normalized_email = self._validate_employee_email(email)
        url = f"{self.auth_base}/signup"
        payload = {"email": normalized_email, "password": password, "data": {"full_name": full_name}}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=self._headers())

        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()

    async def admin_create_user(self, email: str, password: str, full_name: str | None = None) -> dict:
        url = f"{self.admin_base}/users"
        payload = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=self._admin_headers())

        if response.status_code == 422:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists. Please log in.",
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()

    async def login(self, email: str, password: str) -> dict:
        normalized_email = self._validate_employee_email(email)
        url = f"{self.auth_base}/token?grant_type=password"
        payload = {"email": normalized_email, "password": password}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=self._headers())

        if response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        return response.json()

    async def get_user_from_token(self, access_token: str) -> AuthenticatedUser:
        url = f"{self.auth_base}/user"

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=self._headers(access_token))

        if response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

        payload = response.json()
        return AuthenticatedUser(id=payload["id"], email=payload["email"])


auth_service = SupabaseAuthService()
