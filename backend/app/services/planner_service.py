"""Void AI Planner — generates human-level recommendations for void slots.

Uses the deterministic VoidService output and the existing Gemini LLM
to produce an actionable plan for the current free-time slot.  This
service is instantiated *per request* — never cached at module level.
"""

import asyncio
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.services.void_service import VoidService

logger = get_logger(__name__)

_PLANNER_PROMPT_TEMPLATE = """\
You are the VoidFill planner AI.

User has a free time slot.

Void duration: {void_minutes} minutes

Top suggestion:
{title}

Score:
{score}

Write a short recommendation.

Return STRICT JSON only:

{{
  "recommended_goal": "string",
  "recommended_action": "string",
  "confidence": 0-1,
  "reason": "string"
}}
"""


class PlannerService:
    """AI-powered planner that wraps deterministic void detection.

    IMPORTANT: Instantiate inside request handlers only — never at
    module level.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_plan(self, user_id: UUID) -> dict:
        """Generate an AI plan for the user's current void slot.

        Pipeline:
        1. Load deterministic void status (no AI).
        2. If scheduled or no suggestions, return immediately.
        3. Otherwise, call Gemini for a human-level recommendation.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A dict matching ``VoidPlanResponse`` with all fields present.
        """
        # Step 1 — Logging
        logger.info("void_plan_requested", user_id=str(user_id))

        # Step 2 — Load Void Status
        void_service = VoidService(self._session)
        void_status = await void_service.get_void_status(user_id)

        # Step 3 — If Scheduled
        if void_status["status"] == "scheduled":
            return {
                "status": "scheduled",
                "void_minutes": None,
                "recommended_goal": None,
                "recommended_action": None,
                "confidence": None,
                "reason": None,
            }

        # Step 4 — Extract Void Slot
        void_minutes = void_status["void_slot"]["duration_minutes"]

        # Step 5 — Extract Suggestions
        suggestions = void_status["suggestions"]

        # Step 6 — No Suggestions Case
        if not suggestions:
            return {
                "status": "void",
                "void_minutes": void_minutes,
                "recommended_goal": None,
                "recommended_action": None,
                "confidence": None,
                "reason": None,
            }

        # Step 7 — Choose Top Suggestion
        top = suggestions[0]
        title = top["title"]
        score = top["score"]

        # Step 8 — Build Prompt
        prompt = _PLANNER_PROMPT_TEMPLATE.format(
            void_minutes=void_minutes,
            title=title,
            score=score,
        )

        # Step 9 — Call Gemini (non-blocking)
        llm = get_llm_service()
        logger.info("llm_request_started", prompt_length=len(prompt))

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: llm._model.generate_content(prompt),
        )

        raw = response.text.strip()

        # Step 10 — Parse JSON
        data = self._parse_plan_response(raw, title)

        # Step 11 — Logging
        logger.info("void_plan_generated", user_id=str(user_id))

        # Step 12 — Return Response
        return {
            "status": "void",
            "void_minutes": void_minutes,
            "recommended_goal": data["recommended_goal"],
            "recommended_action": data["recommended_action"],
            "confidence": float(data["confidence"]),
            "reason": data["reason"],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_plan_response(raw: str, fallback_title: str) -> dict:
        """Parse the Gemini JSON response with a safe fallback.

        Handles markdown fenced code blocks and malformed JSON
        gracefully — never raises.
        """
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            # Validate required keys exist
            for key in ("recommended_goal", "recommended_action", "confidence", "reason"):
                if key not in data:
                    raise KeyError(key)
            return data
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("planner_json_parse_failed", raw=raw[:200])
            return {
                "recommended_goal": fallback_title,
                "recommended_action": fallback_title,
                "confidence": 0.5,
                "reason": "Fallback plan",
            }
