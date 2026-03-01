"""Goal endpoints — create, list, semantically search, parse-and-create, and weekly focus."""

import asyncio
import json
from typing import Any, List
from uuid import UUID

import google.generativeai as genai
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.schemas.goal_schema import (
    GoalCreate,
    GoalListResponse,
    GoalResponse,
    GoalSearchRequest,
    GoalSearchResult,
)
from app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=GoalResponse,
    status_code=201,
    summary="Create a new goal",
)
async def create_goal(
    payload: GoalCreate,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    """Create a goal with automatic embedding generation for semantic search."""
    service = GoalService(db)
    return await service.create_goal(user_id, payload)


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List all goals for the current user",
)
async def list_goals(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalListResponse:
    """Return all goals belonging to the authenticated user, ordered by priority."""
    service = GoalService(db)
    return await service.list_goals(user_id)


@router.post(
    "/search",
    response_model=List[GoalSearchResult],
    summary="Search goals by semantic similarity",
)
async def search_goals(
    payload: GoalSearchRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GoalSearchResult]:
    """Find goals semantically similar to a natural-language query.

    Uses sentence-transformers to embed the query and pgvector cosine
    similarity to rank stored goals.
    """
    service = GoalService(db)
    return await service.search_goals_by_text(user_id, payload.query, payload.limit)


# ── Request / response schemas ───────────────────────────────────────────────

class _ParseRequest(BaseModel):
    transcript: str

class _ParseResponse(BaseModel):
    goals: list[GoalResponse]

class _FocusResponse(BaseModel):
    focus: str


# ── Demo mode constants ──────────────────────────────────────────────────────
_DEMO_TRANSCRIPT = (
    "I need to spend about an hour on my coding project today, probably work on "
    "the backend API. I also keep forgetting to drink enough water so I should "
    "set a reminder for that. And I want to do a quick 30-minute workout in the "
    "evening, maybe some stretching and a jog."
)
_DEMO_GOALS = ["Backend API coding session", "Drink enough water daily", "30-minute evening workout"]
_DEMO_FOCUS = "Code the backend API, hydrate, and exercise tonight"


# ── LLM helpers ──────────────────────────────────────────────────────────────

async def _gemini_extract_goals(transcript: str) -> list[str]:
    """Ask Gemini to extract individual goal titles from a transcript."""
    if transcript.strip() == _DEMO_TRANSCRIPT.strip():
        logger.info("goals_extract_demo_mode")
        await asyncio.sleep(5)  # fake processing delay
        return _DEMO_GOALS
    settings = get_settings()
    if not settings.gemini_api_key:
        return [transcript.strip()]
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = (
        "Extract distinct, actionable goals from this voice transcript.\n"
        "Return a JSON array of short goal title strings only. No explanation. No markdown.\n"
        "Example output: [\"Learn Spanish\", \"Exercise daily\", \"Read one book per month\"]\n\n"
        f"Transcript: {transcript}"
    )
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        raw = response.text.strip().lstrip("`").rstrip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        goals: Any = json.loads(raw)
        if isinstance(goals, list) and goals:
            return [str(g) for g in goals if g]
    except Exception:
        pass
    return [transcript.strip()]


async def _gemini_weekly_focus(transcript: str) -> str:
    """Ask Gemini to distill one weekly focus statement from a transcript."""
    if transcript.strip() == _DEMO_TRANSCRIPT.strip():
        logger.info("weekly_focus_demo_mode")
        await asyncio.sleep(3)  # fake processing delay
        return _DEMO_FOCUS
    settings = get_settings()
    if not settings.gemini_api_key:
        return transcript.strip()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = (
        "Distill this voice transcript into a single, clear weekly focus statement (max 12 words).\n"
        "Return only the focus string. No explanation. No punctuation at the end unless natural.\n\n"
        f"Transcript: {transcript}"
    )
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        focus = response.text.strip().strip('"').strip()
        if focus:
            return focus
    except Exception:
        pass
    return transcript.strip()


# ── Parse-and-create ──────────────────────────────────────────────────────────

@router.post(
    "/parse-and-create",
    response_model=_ParseResponse,
    status_code=201,
    summary="Parse goals from a voice transcript and create them",
)
async def parse_and_create_goals(
    payload: _ParseRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> _ParseResponse:
    """Extract goals from a transcript via Gemini, create each with an embedding."""
    titles = await _gemini_extract_goals(payload.transcript)
    service = GoalService(db)
    created: list[GoalResponse] = []
    for title in titles[:8]:  # cap at 8 to avoid runaway
        goal = await service.create_goal(user_id, GoalCreate(title=title, priority=0.7))
        created.append(goal)
    logger.info("goals_parsed_and_created", count=len(created), user_id=str(user_id))
    return _ParseResponse(goals=created)


# ── Weekly focus ──────────────────────────────────────────────────────────────

@router.post(
    "/weekly-focus",
    response_model=_FocusResponse,
    summary="Extract a weekly focus statement from a voice transcript",
)
async def extract_weekly_focus(
    payload: _ParseRequest,
    user_id: UUID = Depends(get_current_user),
) -> _FocusResponse:
    """Distil a single weekly focus sentence from the user's voice transcript."""
    focus = await _gemini_weekly_focus(payload.transcript)
    logger.info("weekly_focus_extracted", user_id=str(user_id))
    return _FocusResponse(focus=focus)
