"""Autonomous Action Engine — executes actions based on voice intelligence.

Bridges the gap between intent detection and database mutations:

    intelligence record → intent switch → service call → persisted result
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.note import Note
from app.repositories.note_repository import NoteRepository
from app.repositories.voice_intelligence_repository import VoiceIntelligenceRepository
from app.schemas.goal_schema import GoalCreate
from app.schemas.schedule_schema import ScheduleBlockCreate
from app.services.goal_service import GoalService
from app.services.schedule_service import ScheduleService

logger = get_logger(__name__)


class ActionService:
    """Dispatches autonomous actions derived from voice intelligence records.

    Each supported intent maps to a concrete service call that creates
    the appropriate database entity.  Unknown intents are logged and
    silently skipped.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._intel_repo = VoiceIntelligenceRepository(session)
        self._note_repo = NoteRepository(session)
        self._goal_service = GoalService(session)
        self._schedule_service = ScheduleService(session)

    async def execute_from_intelligence(
        self,
        job_id: UUID,
        user_id: UUID,
    ) -> str:
        """Execute the appropriate action for a voice job's intelligence record.

        Steps:
          1. Load the intelligence record by ``job_id``.
          2. Guard against missing records and duplicate execution.
          3. Dispatch to the handler matching the detected intent.
          4. Mark the record as action-executed for idempotency.

        Args:
            job_id: UUID of the parent VoiceJob.
            user_id: UUID of the owning user.

        Returns:
            A string label describing the action taken (e.g. ``"goal_created"``).

        Raises:
            ValueError: If no intelligence record exists for the given job.
        """
        logger.info("action_started", job_id=str(job_id))

        record = await self._intel_repo.get_by_job_id(job_id)
        if record is None:
            logger.error("action_no_intelligence", job_id=str(job_id))
            raise ValueError(f"No intelligence record for job {job_id}")

        # Idempotency guard — skip if already executed
        if record.action_executed:
            logger.info("action_already_executed", job_id=str(job_id))
            return "already_executed"

        intent = record.intent
        extracted_text = record.extracted_text or ""

        action_label: str

        if intent == "goal_create":
            action_label = await self._handle_goal_create(user_id, extracted_text)
        elif intent in ("schedule_block", "schedule_create"):
            action_label = await self._handle_schedule_block(user_id, extracted_text)
        elif intent in ("note", "note_create"):
            action_label = await self._handle_note(user_id, extracted_text, job_id)
        elif intent == "void_query":
            logger.info("action_void_query", job_id=str(job_id))
            action_label = "void_query"
        else:
            logger.info("action_skipped_unknown_intent", job_id=str(job_id), intent=intent)
            action_label = "no_action"

        # Mark as executed for idempotency
        await self._intel_repo.mark_action_executed(record.id)

        logger.info("action_completed", job_id=str(job_id), action=action_label)
        return action_label

    # ------------------------------------------------------------------
    # Intent handlers
    # ------------------------------------------------------------------

    async def _handle_goal_create(self, user_id: UUID, extracted_text: str) -> str:
        """Create a goal from extracted text.

        Args:
            user_id: The owning user's UUID.
            extracted_text: The cleaned transcript text to use as goal title.

        Returns:
            ``"goal_created"``
        """
        payload = GoalCreate(title=extracted_text, priority=float(0.5))
        goal = await self._goal_service.create_goal(user_id, payload)
        logger.info("goal_created", goal_id=str(goal.id), user_id=str(user_id))
        return "goal_created"

    async def _handle_schedule_block(self, user_id: UUID, extracted_text: str) -> str:
        """Create a schedule block from extracted text.

        Uses UTC timestamps: start = now + 1 hour, end = now + 2 hours.

        Args:
            user_id: The owning user's UUID.
            extracted_text: The cleaned transcript text to use as block type.

        Returns:
            ``"schedule_created"``
        """
        now = datetime.now(timezone.utc)
        payload = ScheduleBlockCreate(
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            block_type=extracted_text[:64] if extracted_text else "voice_block",
        )
        block = await self._schedule_service.create_block(user_id, payload)
        logger.info("schedule_created", block_id=str(block.id), user_id=str(user_id))
        return "schedule_created"

    async def _handle_note(self, user_id: UUID, extracted_text: str, job_id: UUID) -> str:
        """Create a note from extracted text.

        If the voice worker already created a Note for this job_id, update
        its text with the cleaned ``extracted_text`` instead of creating a
        duplicate.

        Args:
            user_id: The owning user's UUID.
            extracted_text: The cleaned transcript text.
            job_id: The originating VoiceJob UUID (foreign key link).

        Returns:
            ``"note_created"`` or ``"note_updated"``
        """
        existing = await self._note_repo.get_by_voice_job_id(job_id)
        if existing is not None:
            existing.text = extracted_text
            await self._note_repo._session.flush()
            logger.info("note_updated", note_id=str(existing.id), user_id=str(user_id))
            return "note_updated"

        note = Note(
            user_id=user_id,
            text=extracted_text,
            voice_job_id=job_id,
        )
        note = await self._note_repo.create_note(note)
        logger.info("note_created", note_id=str(note.id), user_id=str(user_id))
        return "note_created"
