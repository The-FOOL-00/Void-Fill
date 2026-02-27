"""VoiceIntelligence ORM model — stores parsed intent and entity data."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VoiceIntelligence(Base):
    """Structured intelligence extracted from a voice transcript.

    Each record links back to exactly one VoiceJob and optionally to the
    Goal that was matched via semantic search.
    """

    __tablename__ = "voice_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voice_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voice_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    intent: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    goal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    voice_job: Mapped["VoiceJob"] = relationship(lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    goal: Mapped[Optional["Goal"]] = relationship(lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<VoiceIntelligence id={self.id} intent={self.intent}>"
