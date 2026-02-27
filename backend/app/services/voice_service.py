"""Service layer for voice upload and transcription processing."""

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, VoiceProcessingError
from app.core.logging import get_logger
from app.models.voice_log import VoiceLog
from app.repositories.voice_repository import VoiceRepository
from app.schemas.voice_schema import VoiceResultResponse, VoiceUploadResponse

logger = get_logger(__name__)
settings = get_settings()


class VoiceService:
    """Handles voice file ingestion, transcription, and intent detection."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = VoiceRepository(session)
        self._session = session

    async def upload(self, user_id: UUID, file: UploadFile) -> VoiceUploadResponse:
        """Accept a voice file, persist metadata, and return a job id.

        The actual transcription is recorded synchronously for now.
        In production this would dispatch to a background worker (Celery / ARQ).

        Args:
            user_id: The authenticated user's UUID.
            file: The uploaded audio file.

        Returns:
            A response containing the job_id and initial status.

        Raises:
            VoiceProcessingError: If saving the file fails.
        """
        upload_dir = Path(settings.voice_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        job_id = uuid.uuid4()
        file_extension = Path(file.filename or "audio.wav").suffix
        dest = upload_dir / f"{job_id}{file_extension}"

        try:
            content = await file.read()
            dest.write_bytes(content)
        except Exception as exc:
            logger.error("voice_upload_save_failed", error=str(exc), job_id=str(job_id))
            raise VoiceProcessingError(f"Failed to save uploaded file: {exc}") from exc

        transcript = await self._transcribe(dest)
        intent = self._detect_intent(transcript)

        voice_log = VoiceLog(
            id=job_id,
            user_id=user_id,
            transcript=transcript,
            intent=intent,
        )
        await self._repo.create(voice_log)

        logger.info("voice_upload_complete", job_id=str(job_id), intent=intent)
        return VoiceUploadResponse(job_id=job_id, status="completed")

    async def get_result(self, user_id: UUID, job_id: UUID) -> VoiceResultResponse:
        """Retrieve the processing result for a given voice job.

        Args:
            user_id: The authenticated user's UUID.
            job_id: The UUID returned from the upload endpoint.

        Returns:
            A response with transcript and intent data.

        Raises:
            NotFoundError: If no voice log matches the job_id.
        """
        voice_log = await self._repo.get_by_id(job_id)
        if voice_log is None or voice_log.user_id != user_id:
            raise NotFoundError("VoiceLog", job_id)

        return VoiceResultResponse(
            job_id=voice_log.id,
            status="completed",
            transcript=voice_log.transcript,
            intent=voice_log.intent,
            created_at=voice_log.created_at,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _transcribe(self, audio_path: Path) -> str:
        """Run speech-to-text on the given audio file.

        Currently returns a deterministic placeholder transcript.
        The Whisper / faster-whisper integration will replace this body.

        Args:
            audio_path: Path to the saved audio file.

        Returns:
            The transcribed text.
        """
        logger.info("transcription_started", path=str(audio_path))
        # Whisper integration point — replace with actual model call
        return f"[transcript from {audio_path.name}]"

    @staticmethod
    def _detect_intent(transcript: str) -> str:
        """Classify the transcript into a coarse intent category.

        Will be replaced by the LLM parsing service module.

        Args:
            transcript: The transcribed text.

        Returns:
            A string intent label.
        """
        lowered = transcript.lower()
        if any(kw in lowered for kw in ("schedule", "meeting", "calendar", "block")):
            return "schedule"
        if any(kw in lowered for kw in ("goal", "objective", "target", "aim")):
            return "goal"
        if any(kw in lowered for kw in ("suggest", "recommend", "idea", "help")):
            return "suggestion"
        return "general"
