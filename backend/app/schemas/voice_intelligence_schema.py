"""Pydantic schemas for VoiceIntelligence responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceIntelligenceResponse(BaseModel):
    """Schema returned when querying intelligence results for a voice job."""

    job_id: UUID = Field(..., description="The associated voice job UUID")
    intent: str = Field(..., description="Detected intent category")
    confidence: float = Field(..., description="Model confidence score (0.0–1.0)")
    extracted_text: str = Field(..., description="Cleaned extracted text from transcript")
    goal_id: Optional[UUID] = Field(
        default=None, description="UUID of the matched goal, if any"
    )
    created_at: datetime

    model_config = {"from_attributes": True}
