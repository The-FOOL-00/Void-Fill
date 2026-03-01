"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for POST /api/v1/auth/register."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    timezone: str = "UTC"
    language: str = "en"


class LoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned after successful register or login."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
