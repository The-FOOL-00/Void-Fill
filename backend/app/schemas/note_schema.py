"""Pydantic schemas for Note requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NoteResponse(BaseModel):
    """Schema returned when reading a note."""

    id: UUID
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Wrapper for a list of notes."""

    notes: list[NoteResponse]
    count: int
