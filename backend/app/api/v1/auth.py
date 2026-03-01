"""Auth endpoints — register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Create a new account",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user and return a JWT access token."""
    existing = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        timezone=payload.timezone,
        language=payload.language,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=str(user.id))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password and return a JWT access token."""
    result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=str(user.id))


@router.post(
    "/login/token",
    response_model=TokenResponse,
    summary="OAuth2-compatible login (form body)",
    include_in_schema=False,
)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """OAuth2 password flow for /docs Authorize button."""
    result = await db.execute(
        select(User).where(User.email == form.username.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=str(user.id))
