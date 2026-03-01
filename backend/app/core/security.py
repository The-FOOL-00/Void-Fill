"""Security utilities — JWT creation, verification, and FastAPI auth dependency."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing (bcrypt, no passlib dependency)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the hashed password."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/token", auto_error=False)

# Hard-coded demo user kept for backward-compat (no token = demo session)
DEMO_USER_ID: UUID = UUID("00000000-0000-4000-a000-000000000001")


def create_access_token(user_id: UUID, expires_minutes: Optional[int] = None) -> str:
    """Encode a JWT containing the user's UUID as the subject."""
    expire_delta = timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + expire_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(token: Optional[str] = Depends(_oauth2_scheme)) -> UUID:
    """Resolve the authenticated user's UUID from the Bearer token.

    Falls back to the demo user when no token is present so existing
    unauthenticated flows continue to work during transition.

    Raises:
        HTTPException 401: When a token is present but invalid/expired.
    """
    if not token:
        return DEMO_USER_ID

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise JWTError("missing sub")
        return UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
