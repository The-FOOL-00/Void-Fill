"""Reflection endpoint — returns a weekly activity summary for the user."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import google.generativeai as genai
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.goal import Goal
from app.models.schedule_block import ScheduleBlock

router = APIRouter(prefix="/reflection", tags=["reflection"])


# ── Response schema ──────────────────────────────────────────────────────────


class ReflectionStat(BaseModel):
    category: str
    sessions: int
    hours: float
    neglected: bool


class ReflectionResponse(BaseModel):
    week_start: str
    week_end: str
    audio_url: str | None
    summary_text: str | None
    stats: list[ReflectionStat]
    priority_next_week: str | None


# ── Helpers ──────────────────────────────────────────────────────────────────

_CATEGORY_ALIASES: dict[str, str] = {
    "study": "Academic",
    "academic": "Academic",
    "work": "Career",
    "career": "Career",
    "health": "Health & Rest",
    "rest": "Health & Rest",
    "sleep": "Health & Rest",
    "personal": "Personal Growth",
    "growth": "Personal Growth",
    "exercise": "Health & Rest",
    "gym": "Health & Rest",
}

ALL_CATEGORIES = {"Academic", "Career", "Health & Rest", "Personal Growth"}


def _normalise_category(raw: str) -> str:
    return _CATEGORY_ALIASES.get(raw.lower().strip(), raw.title())


def _monday_of_week(dt: datetime) -> datetime:
    """Return 00:00 Monday of the week containing *dt*."""
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.get(
    "/latest",
    response_model=ReflectionResponse,
    summary="Get this week's reflection summary",
)
async def get_latest_reflection(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    now = datetime.now(tz=timezone.utc)
    week_start = _monday_of_week(now)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    # ── Query schedule blocks for the past 7 days ────────────────────────────
    since = now - timedelta(days=7)
    result = await db.execute(
        select(ScheduleBlock).where(
            ScheduleBlock.user_id == user_id,
            ScheduleBlock.start_time >= since,
        )
    )
    blocks = result.scalars().all()

    # ── Aggregate by category ─────────────────────────────────────────────────
    sessions_by_cat: dict[str, int] = defaultdict(int)
    hours_by_cat: dict[str, float] = defaultdict(float)

    for block in blocks:
        cat = _normalise_category(block.block_type)
        sessions_by_cat[cat] += 1
        duration_h = (block.end_time - block.start_time).total_seconds() / 3600
        hours_by_cat[cat] += duration_h

    # Build stats for all known categories (zero if never seen)
    touched = set(sessions_by_cat.keys()) | ALL_CATEGORIES
    stats: list[ReflectionStat] = []
    for cat in sorted(touched):
        s = sessions_by_cat.get(cat, 0)
        h = round(hours_by_cat.get(cat, 0.0), 1)
        stats.append(
            ReflectionStat(
                category=cat,
                sessions=s,
                hours=h,
                neglected=(s == 0),
            )
        )

    # ── Top-priority goal → next-week focus ──────────────────────────────────
    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id)
        .order_by(Goal.priority.desc())
        .limit(1)
    )
    top_goal = goals_result.scalar_one_or_none()
    priority_next_week = top_goal.title if top_goal else None

    # ── Build an AI-generated summary ────────────────────────────────────────────
    total_sessions = sum(sessions_by_cat.values())
    total_hours = round(sum(hours_by_cat.values()), 1)
    neglected = [s.category for s in stats if s.neglected]

    if total_sessions == 0:
        summary_text = (
            "No activity logged this week yet. "
            "Start by adding some schedule blocks or using the mic button."
        )
    else:
        # Build a compact stats description for the Gemini prompt
        stats_lines = ", ".join(
            f"{s.category}: {s.sessions} session(s) / {s.hours}h"
            for s in stats
            if not s.neglected
        )
        neglected_text = f"Neglected areas: {', '.join(neglected)}." if neglected else "No neglected areas."
        goal_text = f"Top goal: {priority_next_week}." if priority_next_week else ""

        prompt = (
            "You are VoidFill AI. Write a 2-3 sentence motivational weekly reflection summary "
            "for a user based on the following stats. Be encouraging and specific. "
            "No markdown, no JSON, just plain text.\n\n"
            f"This week: {total_sessions} session(s), {total_hours} total hours.\n"
            f"Breakdown: {stats_lines}.\n"
            f"{neglected_text}\n"
            f"{goal_text}"
        )
        try:
            settings = get_settings()
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model)

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(prompt)
            )
            summary_text = response.text.strip()
        except Exception:
            # Graceful fallback to rule-based summary
            summary_text = (
                f"You logged {total_sessions} session{'s' if total_sessions != 1 else ''} "
                f"totalling {total_hours} hour{'s' if total_hours != 1.0 else ''} this week."
            )
            if neglected:
                summary_text += f" Areas with no activity: {', '.join(neglected)}."
            if priority_next_week:
                summary_text += f" Top goal for next week: {priority_next_week}."

    return ReflectionResponse(
        week_start=week_start.date().isoformat(),
        week_end=week_end.date().isoformat(),
        audio_url=None,
        summary_text=summary_text,
        stats=stats,
        priority_next_week=priority_next_week,
    )
