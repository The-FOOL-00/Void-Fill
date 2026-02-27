"""Pydantic schemas for ScheduleBlock requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ScheduleBlockCreate(BaseModel):
    """Schema for creating a schedule block."""

    start_time: datetime = Field(..., description="Block start time (ISO-8601)")
    end_time: datetime = Field(..., description="Block end time (ISO-8601)")
    block_type: str = Field(
        ..., min_length=1, max_length=64, description="Type of block (e.g. focus, break, meeting)"
    )

    @model_validator(mode="after")
    def end_after_start(self) -> "ScheduleBlockCreate":
        """Ensure end_time is strictly after start_time."""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_time": "2026-02-27T09:00:00Z",
                    "end_time": "2026-02-27T10:00:00Z",
                    "block_type": "focus",
                }
            ]
        }
    }


class ScheduleBlockResponse(BaseModel):
    """Schema returned when reading a schedule block."""

    id: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime
    block_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleBlockListResponse(BaseModel):
    """Wrapper for a list of schedule blocks."""

    blocks: list[ScheduleBlockResponse]
    count: int
