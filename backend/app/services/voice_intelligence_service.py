"""Voice Intelligence Service — intent detection, entity extraction, goal matching.

Transforms raw transcripts into structured intelligence records by running
a deterministic rule-based pipeline:

    transcript → intent detection → entity extraction → goal matching → persist
"""

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.voice_intelligence import VoiceIntelligence
from app.repositories.goal_repository import GoalRepository
from app.repositories.voice_intelligence_repository import VoiceIntelligenceRepository
from app.services.embedding_service import get_embedding_service

logger = get_logger(__name__)

# ── Intent keyword maps ──────────────────────────────────────────────────

_GOAL_KEYWORDS: tuple[str, ...] = (
    "study", "build", "learn", "practice", "finish", "complete", "improve",
    "read", "write", "create", "develop", "master",
)

_SCHEDULE_KEYWORDS: tuple[str, ...] = (
    "tomorrow", "today", "tonight", "at ", " pm", " am",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "morning", "afternoon", "evening",
    "next week", "o'clock",
)

_NOTE_KEYWORDS: tuple[str, ...] = (
    "remember", "note", "don't forget", "remind", "memo",
)

# ── Filler phrases to strip during entity extraction ─────────────────────

_FILLER_PATTERNS: tuple[str, ...] = (
    r"^i need to\s+",
    r"^i want to\s+",
    r"^i will\s+",
    r"^i should\s+",
    r"^i have to\s+",
    r"^i('d| would) like to\s+",
    r"^please\s+",
    r"^can you\s+",
    r"^could you\s+",
    r"^let me\s+",
    r"^help me\s+",
    r"^i'm going to\s+",
    r"^i am going to\s+",
)


class VoiceIntelligenceService:
    """Processes transcripts into structured intent + entity records.

    Uses rule-based intent detection and existing semantic search for
    goal matching.  Designed to be swapped for an LLM-backed parser in
    a future phase without changing the public API.
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
            1. Detect intent from transcript text.
            2. Extract cleaned entity text.
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

        intent, confidence = self._detect_intent(transcript)
        logger.info(
            "intent_detected",
            voice_job_id=str(voice_job_id),
            intent=intent,
            confidence=confidence,
        )

        extracted_text = self._extract_text(transcript)

        goal_id = await self._match_goal(user_id, extracted_text)
        if goal_id is not None:
            logger.info(
                "goal_matched",
                voice_job_id=str(voice_job_id),
                goal_id=str(goal_id),
            )

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
    # Intent detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_intent(text: str) -> tuple[str, float]:
        """Classify the transcript into one of the supported intents.

        Priority order: goal_create > schedule_block > note > unknown.
        Returns a tuple of ``(intent, confidence)``.

        Args:
            text: Raw transcript text.

        Returns:
            A tuple of the intent label and a confidence score [0..1].
        """
        lowered = text.lower()

        goal_hits = sum(1 for kw in _GOAL_KEYWORDS if kw in lowered)
        schedule_hits = sum(1 for kw in _SCHEDULE_KEYWORDS if kw in lowered)
        note_hits = sum(1 for kw in _NOTE_KEYWORDS if kw in lowered)

        if goal_hits > 0 and goal_hits >= schedule_hits:
            confidence = min(0.5 + goal_hits * 0.15, 1.0)
            return "goal_create", round(confidence, 2)

        if schedule_hits > 0:
            confidence = min(0.5 + schedule_hits * 0.15, 1.0)
            return "schedule_block", round(confidence, 2)

        if note_hits > 0:
            confidence = min(0.5 + note_hits * 0.2, 1.0)
            return "note", round(confidence, 2)

        return "unknown", 0.3

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(text: str) -> str:
        """Clean a transcript by lowering case and stripping filler phrases.

        Args:
            text: Raw transcript text.

        Returns:
            Cleaned, lower-cased text with filler phrases removed.
        """
        cleaned = text.lower().strip()
        for pattern in _FILLER_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, count=1)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

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
