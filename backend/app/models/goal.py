"""Goal ORM model with pgvector embedding support."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector as _PgVector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class SafeVector(TypeDecorator):
    """VECTOR(dim) when pgvector is available, TEXT otherwise.

    The decision is deferred to DDL-generation time so that the flag set
    during init_db() is already in place when create_all() is called.
    """

    impl = Text
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim
        super().__init__()

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        from app.core.database import PGVECTOR_AVAILABLE  # late import

        if PGVECTOR_AVAILABLE:
            return dialect.type_descriptor(_PgVector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        from app.core.database import PGVECTOR_AVAILABLE

        if PGVECTOR_AVAILABLE or value is None:
            return value
        # Fallback: serialise list → JSON string for TEXT storage
        import json

        if isinstance(value, (list, tuple)):
            return json.dumps(list(value))
        return str(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        from app.core.database import PGVECTOR_AVAILABLE

        if PGVECTOR_AVAILABLE or value is None:
            return value
        # Fallback: deserialise JSON string → list
        import json

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


class Goal(Base):
    """Represents a user-defined goal with an optional semantic embedding."""

    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding = mapped_column(SafeVector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="goals")  # type: ignore[name-defined]  # noqa: F821
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="goal", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Goal id={self.id} title={self.title!r}>"
