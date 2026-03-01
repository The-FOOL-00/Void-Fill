"""Application configuration via environment variables using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow fields to be set by both their Python name and any alias
        populate_by_name=True,
    )

    # Application
    app_name: str = "VoidFill"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # PostgreSQL — individual fields (docker-compose / local)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "voidfill"
    postgres_password: str = "voidfill_secret"
    postgres_db: str = "voidfill"

    # Railway-style single-URL override: set DATABASE_URL in Railway dashboard.
    # When present it takes priority over the individual postgres_* fields.
    # Railway provides: postgresql://user:pass@host:port/db
    # This field accepts that exact format; the property below converts scheme.
    database_url_override: Optional[str] = Field(
        default=None, validation_alias="DATABASE_URL"
    )

    # Redis — individual fields (docker-compose / local)
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Railway-style single-URL override: set REDIS_URL in Railway dashboard.
    redis_url_override: Optional[str] = Field(
        default=None, validation_alias="REDIS_URL"
    )

    # Auth (placeholder values for future implementation)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # AI / Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Voice processing
    voice_upload_dir: str = "/tmp/voidfill_voice"
    max_voice_file_size_mb: int = 25
    audio_storage_path: str = "/app/audio"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Gemini — accepts both GEMINI_API_KEY and GOOGLE_API_KEY
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = "gemini-2.5-pro"

    # LLM Provider
    llm_provider: str = "gemini"

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL connection string.

        When DATABASE_URL is set (e.g. Railway addon), it takes priority.
        Railway provides postgresql:// — converted to postgresql+asyncpg://.
        """
        if self.database_url_override:
            url = self.database_url_override
            # SQLAlchemy asyncpg driver requires the +asyncpg scheme variant
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                # Railway sometimes uses the legacy postgres:// scheme
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL connection string for migrations."""
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            return url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis connection string.

        When REDIS_URL is set (e.g. Railway addon), it takes priority.
        """
        if self.redis_url_override:
            return self.redis_url_override
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
