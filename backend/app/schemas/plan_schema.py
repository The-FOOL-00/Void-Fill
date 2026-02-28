"""Pydantic schemas for the Void AI Planner responses."""

from typing import Optional

from pydantic import BaseModel


class VoidPlanResponse(BaseModel):
    """Top-level response for GET /api/v1/void/plan."""

    status: str
    void_minutes: Optional[int] = None
    recommended_goal: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
