"""Async database engine, session factory, and declarative base."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all ORM models."""

    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async database session.

    Commits on success, rolls back on exception, and always closes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables and install pgvector extension.

    Called once during application startup.
    """
    # Import all models so Base.metadata registers every table
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

        # Phase 9 — add estimated_minutes column if it doesn't exist yet
        await conn.execute(text(
            "ALTER TABLE suggestions "
            "ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER"
        ))


async def close_db() -> None:
    """Dispose of the connection pool during shutdown."""
    await engine.dispose()
