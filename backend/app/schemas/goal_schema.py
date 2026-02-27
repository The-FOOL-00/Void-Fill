"""Pydantic schemas for Goal requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """Schema for creating a new goal."""

    title: str = Field(..., min_length=1, max_length=512, description="Goal title")
    priority: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Priority weight between 0 and 1"
    )

    model_config = {"json_schema_extra": {"examples": [{"title": "Learn Spanish", "priority": 0.8}]}}


class GoalResponse(BaseModel):
    """Schema returned when reading a goal."""

    id: UUID
    user_id: UUID
    title: str
    priority: float
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    """Wrapper for paginated goal lists."""

    goals: list[GoalResponse]
    count: int
