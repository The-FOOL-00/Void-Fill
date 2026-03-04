"""Service layer for voice upload and async transcription pipeline."""

import asyncio
import uuid
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, VoiceProcessingError
from app.core.logging import get_logger
from app.core.redis import enqueue_voice_job
from app.models.voice_job import VoiceJob
from app.repositories.voice_job_repository import VoiceJobRepository
from app.schemas.voice_schema import VoiceResultResponse, VoiceUploadResponse

logger = get_logger(__name__)
settings = get_settings()


class VoiceService:
    """Orchestrates voice file ingestion, job creation, and result retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = VoiceJobRepository(session)
        self._session = session

    async def upload(self, user_id: UUID, file: UploadFile) -> VoiceUploadResponse:
        """Accept a voice file, persist it, create a job, and enqueue for processing.

        The endpoint returns immediately with a ``queued`` status.  A background
        worker picks the job off the Redis queue and performs transcription.

        Args:
            user_id: The authenticated user's UUID.
            file: The uploaded audio file.

        Returns:
            A response containing the job_id and ``queued`` status.

        Raises:
            VoiceProcessingError: If saving the audio file to disk fails.
        """
        audio_path = await self._store_audio_file(file)

        job = await self._create_voice_job(user_id, str(audio_path))
        # Commit the job row NOW so it is visible to the inline background task
        # (and to the Redis worker) before we enqueue/schedule processing.
        await self._session.commit()

        await self._enqueue_job(job.id)

        logger.info("voice_upload_accepted", job_id=str(job.id), user_id=str(user_id))
        return VoiceUploadResponse(job_id=job.id, status="queued")

    async def get_result(self, user_id: UUID, job_id: UUID) -> VoiceResultResponse:
        """Retrieve the current status and transcript of a voice job.

        Args:
            user_id: The authenticated user's UUID.
            job_id: The UUID returned from the upload endpoint.

        Returns:
            A response with current status and transcript (null if not yet done).

        Raises:
            NotFoundError: If no voice job matches the job_id for this user.
        """
        job = await self._repo.get_job(job_id)
        if job is None or job.user_id != user_id:
            raise NotFoundError("VoiceJob", job_id)

        return VoiceResultResponse(
            job_id=job.id,
            status=job.status,
            transcript=job.transcript,
            error=job.error,
            created_at=job.created_at,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _store_audio_file(self, file: UploadFile) -> Path:
        """Save the uploaded audio bytes to the configured storage directory.

        Args:
            file: The uploaded audio file.

        Returns:
            The Path to the saved file on disk.

        Raises:
            VoiceProcessingError: If writing the file fails.
        """
        audio_dir = Path(settings.audio_storage_path)
        audio_dir.mkdir(parents=True, exist_ok=True)

        file_extension = Path(file.filename or "audio.wav").suffix
        filename = f"{uuid.uuid4()}{file_extension}"
        dest = audio_dir / filename

        try:
            content = await file.read()
            async with aiofiles.open(dest, "wb") as f:
                await f.write(content)
        except Exception as exc:
            logger.error("voice_file_save_failed", error=str(exc), path=str(dest))
            raise VoiceProcessingError(f"Failed to save uploaded file: {exc}") from exc

        logger.info("voice_file_stored", path=str(dest), size=len(content))
        return dest

    async def _create_voice_job(self, user_id: UUID, audio_path: str) -> VoiceJob:
        """Create and persist a new VoiceJob record with status ``queued``.

        Args:
            user_id: The owning user's UUID.
            audio_path: Absolute path to the stored audio file.

        Returns:
            The persisted VoiceJob instance.
        """
        job = VoiceJob(
            user_id=user_id,
            status="queued",
            audio_path=audio_path,
        )
        return await self._repo.create_job(job)

    @staticmethod
    async def _enqueue_job(job_id: UUID) -> None:
        """Push the job onto the Redis voice processing queue.

        Falls back to inline background processing when Redis is unavailable
        so the upload endpoint never returns 500 due to a missing queue.

        Args:
            job_id: The UUID of the job to enqueue.
        """
        try:
            await enqueue_voice_job(str(job_id))
        except Exception as exc:
            logger.warning(
                "redis_enqueue_failed_fallback_inline",
                job_id=str(job_id),
                error=str(exc),
            )
            # Redis not available — schedule inline processing as a background
            # asyncio task.  process_job() creates its own DB session so it is
            # safe to run outside the current request context.
            from app.workers.voice_worker import process_job  # local import to avoid circular deps

            asyncio.create_task(process_job(str(job_id)), name=f"voice-job-{job_id}")
