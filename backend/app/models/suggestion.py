"""Suggestion ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Suggestion(Base):
    """An AI-generated suggestion optionally linked to a goal."""

    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(String(1024), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="suggestions")  # type: ignore[name-defined]  # noqa: F821
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="suggestions")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Suggestion id={self.id} score={self.score}>"
