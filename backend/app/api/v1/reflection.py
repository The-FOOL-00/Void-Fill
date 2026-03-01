"""Reflection endpoint — returns a weekly activity summary for the user."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


# ── Demo fallback data (shown when no real activity exists yet) ───────────────

_DEMO_STATS = [
    ReflectionStat(category="Academic",        sessions=3, hours=4.5, neglected=False),
    ReflectionStat(category="Career",          sessions=5, hours=7.0, neglected=False),
    ReflectionStat(category="Health & Rest",   sessions=2, hours=1.5, neglected=False),
    ReflectionStat(category="Personal Growth", sessions=1, hours=0.5, neglected=False),
]
_DEMO_SUMMARY = (
    "Great week! You kept your career on track with 5 focused sessions, "
    "balanced academics with solid study hours, and made time for health and personal growth. "
    "Keep that momentum going — next week is yours to own."
)


# ── Helpers ──────────────────────────────────────────────────────────────────

_CATEGORY_ALIASES: dict[str, str] = {
    # Academic
    "study": "Academic",
    "academic": "Academic",
    "exam": "Academic",
    "homework": "Academic",
    "class": "Academic",
    "lecture": "Academic",
    "assignment": "Academic",
    "read": "Academic",
    "learn": "Academic",
    # Career
    "work": "Career",
    "career": "Career",
    "api": "Career",
    "coding": "Career",
    "backend": "Career",
    "frontend": "Career",
    "project": "Career",
    "meeting": "Career",
    "job": "Career",
    "interview": "Career",
    "milestone": "Career",
    "sprint": "Career",
    # Health & Rest
    "health": "Health & Rest",
    "rest": "Health & Rest",
    "sleep": "Health & Rest",
    "exercise": "Health & Rest",
    "workout": "Health & Rest",
    "gym": "Health & Rest",
    "run": "Health & Rest",
    "walk": "Health & Rest",
    "jog": "Health & Rest",
    "yoga": "Health & Rest",
    "swim": "Health & Rest",
    "water": "Health & Rest",
    "drink": "Health & Rest",
    # Personal Growth
    "personal": "Personal Growth",
    "growth": "Personal Growth",
    "habit": "Personal Growth",
    "skill": "Personal Growth",
    "guitar": "Personal Growth",
    "journal": "Personal Growth",
    "meditat": "Personal Growth",
}

ALL_CATEGORIES = {"Academic", "Career", "Health & Rest", "Personal Growth"}


def _normalise_category(raw: str) -> str | None:
    """Return a canonical category for *raw*, or None if unrecognised."""
    text = raw.lower()
    for keyword, category in _CATEGORY_ALIASES.items():
        if keyword in text:
            return category
    return None


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

    # Deduplicate blocks by block_type — keep only the earliest per type
    seen_types: set[str] = set()
    unique_blocks = []
    for b in sorted(blocks, key=lambda x: x.start_time):
        if b.block_type not in seen_types:
            seen_types.add(b.block_type)
            unique_blocks.append(b)

    # ── Aggregate schedule blocks by category ────────────────────────────────
    sessions_by_cat: dict[str, int] = defaultdict(int)
    hours_by_cat: dict[str, float] = defaultdict(float)

    for block in unique_blocks:
        cat = _normalise_category(block.block_type)
        if cat is None:
            continue  # skip unrecognised block_types (e.g. "autonomy")
        sessions_by_cat[cat] += 1
        duration_h = (block.end_time - block.start_time).total_seconds() / 3600
        hours_by_cat[cat] += duration_h

    # ── Also count goals per category ────────────────────────────────────────
    all_goals_result = await db.execute(
        select(Goal).where(Goal.user_id == user_id).order_by(Goal.priority.desc())
    )
    all_goals = all_goals_result.scalars().all()

    goals_by_cat: dict[str, int] = defaultdict(int)
    seen_goal_titles: set[str] = set()
    for goal in all_goals:
        title_key = goal.title.strip().lower()
        if title_key in seen_goal_titles:
            continue
        seen_goal_titles.add(title_key)
        cat = _normalise_category(goal.title)
        if cat:
            goals_by_cat[cat] += 1

    # Build stats — only show the 4 canonical categories
    stats: list[ReflectionStat] = []
    for cat in sorted(ALL_CATEGORIES):
        s = sessions_by_cat.get(cat, 0)
        h = round(hours_by_cat.get(cat, 0.0), 1)
        g = goals_by_cat.get(cat, 0)
        stats.append(
            ReflectionStat(
                category=cat,
                # Count both time-blocked sessions AND active goals
                sessions=s + g,
                hours=h,
                neglected=(s == 0 and g == 0),
            )
        )

    # ── Top-priority goal → next-week focus (reuse already-fetched list) ─────
    top_goal = all_goals[0] if all_goals else None
    priority_next_week = top_goal.title if top_goal else None

    # ── Build summary ─────────────────────────────────────────────────────────
    total_block_sessions = sum(sessions_by_cat.values())
    total_goal_count = sum(goals_by_cat.values())
    total_hours = round(sum(hours_by_cat.values()), 1)
    neglected = [s.category for s in stats if s.neglected]

    if total_block_sessions == 0 and total_goal_count == 0:
        # No activity at all — return demo data so the page looks meaningful
        return ReflectionResponse(
            week_start=week_start.date().isoformat(),
            week_end=week_end.date().isoformat(),
            audio_url=None,
            summary_text=_DEMO_SUMMARY,
            stats=_DEMO_STATS,
            priority_next_week=priority_next_week,
        )
    else:
        total_sessions = total_block_sessions + total_goal_count
        summary_text = (
            f"You have {total_sessions} active goal{'s' if total_sessions != 1 else ''} "
            f"and logged {total_hours} hour{'s' if total_hours != 1.0 else ''} this week. "
            "Great work staying focused across your goals!"
        )
        if neglected:
            summary_text += f" Areas to grow next week: {', '.join(neglected)}."
        if priority_next_week:
            summary_text += f" Top priority: {priority_next_week}."

    return ReflectionResponse(
        week_start=week_start.date().isoformat(),
        week_end=week_end.date().isoformat(),
        audio_url=None,
        summary_text=summary_text,
        stats=stats,
        priority_next_week=priority_next_week,
    )
