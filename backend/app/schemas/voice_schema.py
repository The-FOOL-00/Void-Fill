"""Pydantic schemas for voice upload requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceUploadResponse(BaseModel):
    """Returned immediately after a voice file is accepted for processing."""

    job_id: UUID = Field(..., description="Unique identifier for the processing job")
    status: str = Field(default="processing", description="Current job status")


class VoiceResultResponse(BaseModel):
    """Returned when querying the result of a voice processing job."""

    job_id: UUID
    status: str = Field(..., description="processing | completed | failed")
    transcript: str = Field(default="", description="Transcribed text")
    intent: str = Field(default="unknown", description="Detected intent")
    created_at: datetime

    model_config = {"from_attributes": True}
