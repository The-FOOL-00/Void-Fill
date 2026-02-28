"""Pydantic schemas for Suggestion requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SuggestionRequest(BaseModel):
    """Schema for requesting new AI suggestions."""

    goal_id: Optional[UUID] = Field(
        default=None, description="Optionally scope suggestions to a specific goal"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum suggestions to generate")

    model_config = {
        "json_schema_extra": {
            "examples": [{"goal_id": None, "limit": 5}]
        }
    }


class SuggestionResponse(BaseModel):
    """Schema returned for a single suggestion."""

    id: UUID
    user_id: UUID
    goal_id: Optional[UUID]
    text: str
    score: float
    estimated_minutes: Optional[int] = None
    accepted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionListResponse(BaseModel):
    """Wrapper for a list of suggestions."""

    suggestions: list[SuggestionResponse]
    count: int
