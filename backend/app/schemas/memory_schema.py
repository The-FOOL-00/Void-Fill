"""Pydantic schemas for the Memory Engine."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryRecordRequest(BaseModel):
    """Schema for recording a new memory."""

    goal_id: Optional[UUID] = Field(default=None, description="Associated goal UUID")
    title: str = Field(..., min_length=1, max_length=512, description="Action title")
    minutes: int = Field(..., gt=0, description="Duration in minutes")


class MemoryGoalSummary(BaseModel):
    """Aggregated summary of a single goal's sessions."""

    goal_id: Optional[UUID]
    title: str
    sessions: int
    total_minutes: int

    model_config = {"from_attributes": True}


class MemoryActionSummary(BaseModel):
    """A single recent action."""

    title: str
    minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MemorySummaryResponse(BaseModel):
    """Complete memory summary returned by GET /memory/summary."""

    top_goals: list[MemoryGoalSummary]
    recent_actions: list[MemoryActionSummary]
