"""Pydantic schemas for the Autonomy Engine responses."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AutonomyResponse(BaseModel):
    """Response returned by POST /api/v1/autonomy/run."""

    status: str = Field(..., description="'scheduled' or 'skipped'")
    reason: str = Field(..., description="Human-readable explanation")
    block_id: Optional[UUID] = None
    void_minutes: int = Field(..., ge=0)
    suggestion_title: Optional[str] = None
