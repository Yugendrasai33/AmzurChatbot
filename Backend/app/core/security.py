from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.services.auth_service import AuthenticatedUser, auth_service
from app.services.auth_service import verify_local_jwt


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    parts = authorization.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header format")

    return parts[1]


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    token = _extract_bearer_token(authorization)
    # Try Supabase token validation first (email/password users).
    try:
        return await auth_service.get_user_from_token(token)
    except HTTPException:
        pass
    # Fall back to locally-signed JWT (Google-authenticated users).
    return verify_local_jwt(token)
