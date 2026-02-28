"""Autonomy Engine — AI-guided void-fill pipeline.

Detects void slots, gathers suggestions + memory + habits, asks Gemini
to choose the best action, then creates a schedule block and records
memory.  Manual trigger only (POST /api/v1/autonomy/run).

Pipeline:
    Void → Suggestions → Memory → Habits → Gemini Decision → Schedule → Memory
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.schemas.schedule_schema import ScheduleBlockCreate
from app.services.habit_service import HabitService
from app.services.llm_service import get_llm_service
from app.services.memory_service import MemoryService
from app.services.schedule_service import ScheduleService
from app.services.suggestion_service import SuggestionService
from app.services.void_service import VoidService

logger = get_logger(__name__)

_AUTONOMY_PROMPT = """\
You are the VoidFill autonomy AI.

User has free time.

Void duration:
{void_minutes} minutes

Suggestions:
{suggestions_text}

User Memory:
{memory_text}

User Habits:
{habit_text}

Choose the best action.

Return STRICT JSON:

{{
  "decision": "schedule | skip",
  "title": "string or null",
  "duration_minutes": number or null,
  "confidence": 0-1,
  "reason": "string"
}}
"""


class AutonomyService:
    """AI-guided autonomy pipeline — one block per invocation.

    IMPORTANT: Instantiated *per request* — never cached at module level.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_autonomy(self, user_id: UUID) -> dict:
        """Execute the full AI-guided autonomy pipeline.

        Pipeline:
        Schedule → Void Detection → Suggestion Ranking →
        Memory → Habits → Gemini Decision →
        Schedule Creation → Memory Recording

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A JSON-serialisable dict matching ``AutonomyResponse``.
        """
        # Step 1 — Logging
        logger.info("autonomy_run_started", user_id=str(user_id))

        # Step 2 — Load void status
        void_service = VoidService(self._session)
        void_status = await void_service.get_void_status(user_id)

        # Step 3 — If user is currently scheduled, skip (NO AI CALL)
        if void_status["status"] == "scheduled":
            return {
                "status": "skipped",
                "reason": "User currently scheduled",
                "block_id": None,
                "void_minutes": 0,
                "suggestion_title": None,
            }

        # Step 4 — Extract void slot
        void_slot = void_status.get("void_slot")
        if void_slot is None:
            return {
                "status": "skipped",
                "reason": "No void slot detected",
                "block_id": None,
                "void_minutes": 0,
                "suggestion_title": None,
            }

        void_minutes: int = void_slot["duration_minutes"]

        # Step 5 — Minimum duration check (NO AI CALL)
        if void_minutes < 15:
            return {
                "status": "skipped",
                "reason": "Void too small",
                "block_id": None,
                "void_minutes": void_minutes,
                "suggestion_title": None,
            }

        # Step 6 — Load ranked suggestions
        suggestion_service = SuggestionService(self._session)
        ranked = await suggestion_service.get_ranked_suggestions(
            user_id,
            void_minutes=void_minutes,
        )

        # Step 7 — No suggestions available (NO AI CALL)
        if not ranked:
            return {
                "status": "skipped",
                "reason": "No suggestions available",
                "block_id": None,
                "void_minutes": void_minutes,
                "suggestion_title": None,
            }

        # Step 8 — Load memory summary
        memory_service = MemoryService(self._session)
        memory = await memory_service.get_summary(user_id)
        logger.info("memory_summary_requested")

        # Step 9 — Load habit summary
        habit_service = HabitService(self._session)
        habits = await habit_service.get_summary(user_id)

        # Step 10 — Build suggestion text (top 5)
        suggestions_text = self._build_suggestions_text(ranked[:5])

        # Step 11 — Build memory text
        memory_text = self._build_memory_text(memory)

        # Step 12 — Build habit text
        habit_text = self._build_habit_text(habits)

        # Step 13 — Build AI decision prompt
        prompt = _AUTONOMY_PROMPT.format(
            void_minutes=void_minutes,
            suggestions_text=suggestions_text,
            memory_text=memory_text,
            habit_text=habit_text,
        )

        # Step 14 — LLM call (non-blocking)
        ai_decision = await self._call_llm(prompt, ranked, void_minutes)

        # Step 15 is handled inside _call_llm (parse + fallback)

        logger.info(
            "autonomy_ai_decision",
            decision=ai_decision.get("decision"),
            title=ai_decision.get("title"),
            confidence=ai_decision.get("confidence"),
        )

        # Step 16 — If AI says skip
        if ai_decision["decision"] == "skip":
            return {
                "status": "skipped",
                "reason": ai_decision.get("reason", "AI decided to skip"),
                "block_id": None,
                "void_minutes": void_minutes,
                "suggestion_title": None,
            }

        # Step 17 — Validate suggestion exists
        ai_title: str = ai_decision.get("title") or ""
        matched_suggestion = None
        for _score, s in ranked:
            if s.text.lower() == ai_title.lower():
                matched_suggestion = s
                break
        if matched_suggestion is None:
            # Fallback to top suggestion
            _score, matched_suggestion = ranked[0]

        title: str = matched_suggestion.text
        goal_id: UUID | None = matched_suggestion.goal_id

        # Step 18 — Validate duration
        ai_duration: int | None = ai_decision.get("duration_minutes")
        if ai_duration is not None and isinstance(ai_duration, (int, float)):
            duration = int(min(ai_duration, void_minutes))
        else:
            duration = min(30, void_minutes)
        if duration < 5:
            duration = 15

        # Step 19 — Create schedule block
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=duration)

        schedule_service = ScheduleService(self._session)
        payload = ScheduleBlockCreate(
            start_time=start_time,
            end_time=end_time,
            block_type="autonomy",
        )
        block_response = await schedule_service.create_block(
            user_id=user_id,
            payload=payload,
        )
        await self._session.commit()

        # Step 20 — Record memory
        await memory_service.record_action(
            user_id=user_id,
            goal_id=goal_id,
            title=title,
            minutes=duration,
        )
        await self._session.commit()

        # Step 21 — Logging
        logger.info(
            "autonomy_block_created",
            block_id=str(block_response.id),
            minutes=duration,
        )

        # Step 22 — Return response
        ai_reason = ai_decision.get("reason", "Autonomy scheduled task")
        return {
            "status": "scheduled",
            "reason": ai_reason,
            "block_id": block_response.id,
            "void_minutes": void_minutes,
            "suggestion_title": title,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        prompt: str,
        ranked: list,
        void_minutes: int,
    ) -> dict[str, Any]:
        """Call Gemini with the autonomy prompt and return parsed decision.

        Falls back to a deterministic schedule decision on any failure
        so the pipeline never crashes.
        """
        logger.info("llm_request_started")

        # Deterministic fallback
        _fallback_score, fallback_suggestion = ranked[0]
        fallback: dict[str, Any] = {
            "decision": "schedule",
            "title": fallback_suggestion.text,
            "duration_minutes": min(
                fallback_suggestion.estimated_minutes or 30,
                void_minutes,
            ),
            "confidence": 0.5,
            "reason": "Autonomy scheduled task",
        }

        try:
            llm = get_llm_service()
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: llm._model.generate_content(prompt),
            )
            raw = response.text.strip()
            logger.info("llm_response_received", raw_length=len(raw))
            return self._parse_ai_decision(raw, fallback)
        except Exception as exc:
            logger.error("llm_autonomy_failed", error=str(exc))
            return fallback

    @staticmethod
    def _parse_ai_decision(raw: str, fallback: dict[str, Any]) -> dict[str, Any]:
        """Parse JSON from LLM response with safe fallback."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("llm_autonomy_json_parse_failed", raw=raw[:200])
            return fallback

        decision = data.get("decision", "schedule")
        if decision not in ("schedule", "skip"):
            decision = "schedule"

        title = data.get("title")
        duration = data.get("duration_minutes")
        reason = data.get("reason", "AI decision")

        try:
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5

        return {
            "decision": decision,
            "title": title,
            "duration_minutes": duration,
            "confidence": round(confidence, 2),
            "reason": reason,
        }

    @staticmethod
    def _build_suggestions_text(ranked: list) -> str:
        """Format top ranked suggestions as numbered text."""
        lines: list[str] = []
        for idx, (score, s) in enumerate(ranked, 1):
            est = s.estimated_minutes or "unknown"
            lines.append(
                f"{idx}. {s.text}\n"
                f"   score={score:.2f}\n"
                f"   estimated_minutes={est}"
            )
        return "\n\n".join(lines) if lines else "No suggestions available."

    @staticmethod
    def _build_memory_text(memory: dict) -> str:
        """Format memory summary as human-readable text."""
        parts: list[str] = []

        top_goals = (memory.get("top_goals") or [])[:3]
        if top_goals:
            parts.append("Top Goals:")
            for g in top_goals:
                title = g.get("title", "Unknown")
                sessions = g.get("sessions", 0)
                minutes = g.get("total_minutes", 0)
                parts.append(f"  {title}: sessions={sessions}, minutes={minutes}")

        recent = (memory.get("recent_actions") or [])[:5]
        if recent:
            parts.append("\nRecent Actions:")
            for a in recent:
                parts.append(f"  {a.get('title', 'Unknown')}: {a.get('minutes', 0)} min")

        return "\n".join(parts) if parts else "No memory data."

    @staticmethod
    def _build_habit_text(habits: dict) -> str:
        """Format habit summary as human-readable text."""
        top = (habits.get("top_habits") or [])[:3]
        if not top:
            return "No habit data."

        lines: list[str] = []
        for h in top:
            title = h.get("goal_title", "Unknown")
            sessions = h.get("sessions", 0)
            minutes = h.get("total_minutes", 0)
            lines.append(f"{title}:\n  sessions={sessions}\n  minutes={minutes}")
        return "\n\n".join(lines)
