"""User ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Represents an application user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(320), unique=True, nullable=True, index=True
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")

    # Relationships
    goals: Mapped[list["Goal"]] = relationship(back_populates="user", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    schedule_blocks: Mapped[list["ScheduleBlock"]] = relationship(back_populates="user", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    voice_logs: Mapped[list["VoiceLog"]] = relationship(back_populates="user", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="user", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
