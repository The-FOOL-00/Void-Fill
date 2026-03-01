"""Async database engine, session factory, and declarative base."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Set to True in init_db() when the pgvector extension is successfully installed.
# Models read this flag at DDL-generation time (create_all) to decide whether
# to use VECTOR(384) or TEXT for embedding columns.
PGVECTOR_AVAILABLE: bool = False

_connect_args: dict = {}
if settings.database_use_ssl:
    # Neon (and other managed Postgres) require SSL. asyncpg uses connect_args
    # rather than sslmode in the URL, which is stripped in config.database_url.
    import ssl as _ssl
    _ssl_ctx = _ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = _ssl.CERT_NONE
    _connect_args = {"ssl": _ssl_ctx}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_connect_args,
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
    global PGVECTOR_AVAILABLE

    # Step 1: try to install pgvector in its own autocommit connection so a
    # failure doesn't poison the transaction used by create_all below.
    try:
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        PGVECTOR_AVAILABLE = True
        logger.info("pgvector extension is available — vector search enabled.")
    except Exception as e:
        PGVECTOR_AVAILABLE = False
        logger.warning(
            "pgvector extension not available — embedding columns will use TEXT. "
            "To enable vector search, use a pgvector-enabled PostgreSQL. Error: %s", e
        )

    # Step 2: import all models AFTER setting PGVECTOR_AVAILABLE so that
    # SafeVector TypeDecorator resolves to the correct SQL type at DDL time.
    import app.models  # noqa: F401

    # Step 3: create / migrate tables in a normal transaction.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Additive migrations — safe to run on every startup
        await conn.execute(text(
            "ALTER TABLE suggestions "
            "ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER"
        ))
        await conn.execute(text(
            "ALTER TABLE users "
            "ADD COLUMN IF NOT EXISTS email VARCHAR(320)"
        ))
        await conn.execute(text(
            "ALTER TABLE users "
            "ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(256)"
        ))
        # Unique index on email — CREATE IF NOT EXISTS equivalent
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email "
            "ON users (email) WHERE email IS NOT NULL"
        ))


async def close_db() -> None:
    """Dispose of the connection pool during shutdown."""
    await engine.dispose()
