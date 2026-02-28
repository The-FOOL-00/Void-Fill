"""Pydantic schemas for the Habit Engine."""

from pydantic import BaseModel, Field


class HabitSummaryItem(BaseModel):
    """A single habit derived from memory data."""

    goal_title: str = Field(..., description="Title of the goal / action")
    sessions: int = Field(..., description="Number of recorded sessions")
    total_minutes: int = Field(..., description="Total minutes spent")
    habit_strength: float = Field(..., ge=0, le=1, description="Strength score 0–1")


class TimePatternItem(BaseModel):
    """Hour-of-day activity pattern."""

    hour: int = Field(..., ge=0, le=23, description="Hour of day (0–23)")
    sessions: int = Field(..., description="Number of sessions in this hour")


class HabitSummaryResponse(BaseModel):
    """Complete habit summary returned by GET /habits/summary."""

    top_habits: list[HabitSummaryItem]
    time_patterns: list[TimePatternItem]
    avg_session_minutes: int
