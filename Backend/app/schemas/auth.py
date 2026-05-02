from pydantic import BaseModel


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: AuthUser
