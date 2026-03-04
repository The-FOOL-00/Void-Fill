"""Pydantic schemas for voice upload requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceUploadResponse(BaseModel):
    """Returned immediately after a voice file is accepted for processing."""

    job_id: UUID = Field(..., description="Unique identifier for the processing job")
    status: str = Field(default="queued", description="Current job status")


class VoiceResultResponse(BaseModel):
    """Returned when querying the result of a voice processing job."""

    job_id: UUID
    status: str = Field(..., description="queued | processing | completed | failed")
    transcript: Optional[str] = Field(default=None, description="Transcribed text (null until completed)")
    error: Optional[str] = Field(default=None, description="Error message if job failed")
    created_at: datetime

    model_config = {"from_attributes": True}
