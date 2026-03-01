"""Pydantic schemas for the Void Intelligence Engine responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.schedule_schema import ScheduleBlockResponse


class VoidSlotResponse(BaseModel):
    """A detected void (free time) slot."""

    start_time: datetime
    end_time: datetime
    duration_minutes: int = Field(..., ge=0)


class VoidSuggestion(BaseModel):
    """A lightweight suggestion surfaced in the void response."""

    id: Optional[UUID] = None
    goal_id: Optional[UUID] = None
    title: str
    score: float


class VoidNowResponse(BaseModel):
    """Top-level response for GET /api/v1/void/now."""

    status: str = Field(..., description="'void' or 'scheduled'")
    current_block: Optional[ScheduleBlockResponse] = None
    void_slot: Optional[VoidSlotResponse] = None
    suggestions: list[VoidSuggestion] = Field(default_factory=list)
