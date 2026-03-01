"""Voice Intelligence Service — LLM-powered intent detection and entity extraction.

Transforms raw transcripts into structured intelligence records by
calling the LLM intelligence engine:

    transcript → LLM analysis → goal matching → persist
"""

import asyncio
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.voice_intelligence import VoiceIntelligence
from app.repositories.goal_repository import GoalRepository
from app.repositories.voice_intelligence_repository import VoiceIntelligenceRepository
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)

# ── Demo mode: bypass Gemini entirely ────────────────────────────────────────
_DEMO_TRANSCRIPT = (
    "I need to spend about an hour on my coding project today, probably work on "
    "the backend API. I also keep forgetting to drink enough water so I should "
    "set a reminder for that. And I want to do a quick 30-minute workout in the "
    "evening, maybe some stretching and a jog."
)
_DEMO_LLM_RESULT: dict = {
    "intent": "goal_create",
    "confidence": 0.95,
    "goal_title": "Backend API coding session",
    "note_text": None,
    "schedule_activity": None,
    "schedule_time": None,
}


class VoiceIntelligenceService:
    """Processes transcripts into structured intent + entity records.

    Uses Gemini for intent detection and entity extraction, with
    existing semantic search for goal matching.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._intel_repo = VoiceIntelligenceRepository(session)
        self._goal_repo = GoalRepository(session)
        self._embedding = get_embedding_service()

    async def process_transcript(
        self,
        voice_job_id: UUID,
        user_id: UUID,
        transcript: str,
    ) -> VoiceIntelligence:
        """Run the full intelligence pipeline on a transcript.

        Steps:
            1. Send transcript to LLM for structured analysis.
            2. Extract intent, confidence, and entity text.
            3. Attempt semantic goal matching.
            4. Persist a ``VoiceIntelligence`` record.

        Args:
            voice_job_id: UUID of the parent VoiceJob.
            user_id: UUID of the owning user.
            transcript: Raw transcript text.

        Returns:
            The persisted VoiceIntelligence record.
        """
        logger.info("transcript_received", voice_job_id=str(voice_job_id))

        # ── LLM analysis (skip if demo transcript) ────────────────────
        if transcript.strip() == _DEMO_TRANSCRIPT.strip():
            logger.info("llm_skipped_demo_mode", voice_job_id=str(voice_job_id))
            await asyncio.sleep(5)  # Fake processing delay so the UI feels real
            llm_result = _DEMO_LLM_RESULT
        else:
            llm_service = get_llm_service()
            llm_result = await llm_service.analyze_transcript(transcript)

        intent = llm_result["intent"]
        confidence = llm_result["confidence"]

        # Derive the best extracted text from the LLM structured fields
        if intent in ("schedule_create", "schedule_block"):
            # Store activity and time together so action_service can use both
            activity = llm_result.get("schedule_activity") or ""
            time_str = llm_result.get("schedule_time") or ""
            extracted_text = f"{activity}|||{time_str}"
        else:
            extracted_text = (
                llm_result.get("goal_title")
                or llm_result.get("note_text")
                or llm_result.get("schedule_time")
                or transcript.strip()
            )

        logger.info(
            "intent_detected",
            voice_job_id=str(voice_job_id),
            intent=intent,
            confidence=confidence,
        )

        # ── Goal matching ────────────────────────────────────────────
        goal_id = await self._match_goal(user_id, extracted_text)
        if goal_id is not None:
            logger.info(
                "goal_matched",
                voice_job_id=str(voice_job_id),
                goal_id=str(goal_id),
            )

        # ── Persist ──────────────────────────────────────────────────
        record = VoiceIntelligence(
            voice_job_id=voice_job_id,
            intent=intent,
            confidence=confidence,
            extracted_text=extracted_text,
            goal_id=goal_id,
        )
        record = await self._intel_repo.create_intelligence_record(record)

        logger.info("intelligence_saved", voice_job_id=str(voice_job_id))
        return record

    # ------------------------------------------------------------------
    # Goal matching
    # ------------------------------------------------------------------

    async def _match_goal(
        self, user_id: UUID, extracted_text: str
    ) -> Optional[UUID]:
        """Attempt to find a semantically matching goal.

        Generates an embedding for the extracted text and queries
        pgvector for the closest user goal.  Returns ``None`` if no
        goals exist for the user.

        Args:
            user_id: UUID of the owning user.
            extracted_text: Cleaned text to match against.

        Returns:
            The UUID of the best-matching goal, or ``None``.
        """
        if not extracted_text:
            return None

        try:
            query_embedding = await self._embedding.generate_embedding(extracted_text)
            goals = await self._goal_repo.search_by_embedding(
                user_id=user_id,
                embedding=query_embedding,
                limit=1,
            )
            if goals:
                return goals[0].id
        except Exception as exc:
            logger.warning(
                "goal_matching_failed",
                user_id=str(user_id),
                error=str(exc),
            )
        return None
