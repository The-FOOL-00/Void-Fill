"""VoidFill — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import goals, notes, schedule, suggestions, voice, void
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    VoidFillError,
)
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    setup_logging()
    logger.info("starting_application", version=settings.app_version, env=settings.environment)

    await init_db()
    logger.info("database_initialised")

    # Ensure demo user exists so endpoints work out of the box
    await _ensure_demo_user()

    yield

    await close_db()
    logger.info("application_shutdown")


async def _ensure_demo_user() -> None:
    """Insert the hard-coded demo user if it does not already exist."""
    from app.core.database import async_session_factory
    from app.core.security import DEMO_USER_ID
    from app.models.user import User
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == DEMO_USER_ID))
        if result.scalar_one_or_none() is None:
            session.add(User(id=DEMO_USER_ID, timezone="UTC", language="en"))
            await session.commit()
            logger.info("demo_user_created", user_id=str(DEMO_USER_ID))


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Voice-first AI productivity copilot",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow all origins during development; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Return 404 for missing resources."""
    return JSONResponse(status_code=404, content={"code": exc.code, "message": exc.message})


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Return 422 for business-rule validation failures."""
    return JSONResponse(
        status_code=422,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(AuthenticationError)
async def auth_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Return 401 for authentication failures."""
    return JSONResponse(status_code=401, content={"code": exc.code, "message": exc.message})


@app.exception_handler(AuthorizationError)
async def authz_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Return 403 for authorization failures."""
    return JSONResponse(status_code=403, content={"code": exc.code, "message": exc.message})


@app.exception_handler(VoidFillError)
async def generic_app_handler(request: Request, exc: VoidFillError) -> JSONResponse:
    """Catch-all for any other VoidFill application errors."""
    return JSONResponse(status_code=500, content={"code": exc.code, "message": exc.message})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"], summary="Health check")
async def health() -> dict:
    """Return application health status and metadata."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


# ---------------------------------------------------------------------------
# Versioned routes
# ---------------------------------------------------------------------------

app.include_router(voice.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(schedule.router, prefix="/api/v1")
app.include_router(suggestions.router, prefix="/api/v1")
app.include_router(void.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
