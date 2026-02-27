"""Repository for VoiceJob database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_job import VoiceJob


class VoiceJobRepository:
    """Encapsulates all database access for the VoiceJob model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, job: VoiceJob) -> VoiceJob:
        """Persist a new VoiceJob to the database.

        Args:
            job: A fully populated VoiceJob ORM instance.

        Returns:
            The persisted VoiceJob with server-generated fields populated.
        """
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> VoiceJob | None:
        """Fetch a single voice job by primary key.

        Args:
            job_id: UUID of the voice job.

        Returns:
            The VoiceJob if found, otherwise ``None``.
        """
        stmt = select(VoiceJob).where(VoiceJob.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, job_id: UUID, status: str) -> VoiceJob | None:
        """Update the status field of a voice job.

        Args:
            job_id: UUID of the voice job.
            status: New status value (queued, processing, completed, failed).

        Returns:
            The updated VoiceJob, or ``None`` if not found.
        """
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.status = status
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def update_transcript(self, job_id: UUID, transcript: str) -> VoiceJob | None:
        """Store the transcription result without changing job status.

        Args:
            job_id: UUID of the voice job.
            transcript: The transcribed text.

        Returns:
            The updated VoiceJob, or ``None`` if not found.
        """
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.transcript = transcript
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_completed(self, job_id: UUID) -> VoiceJob | None:
        """Mark a voice job as completed.

        Args:
            job_id: UUID of the voice job.

        Returns:
            The updated VoiceJob, or ``None`` if not found.
        """
        return await self.update_status(job_id, "completed")

    async def update_error(self, job_id: UUID, error: str) -> VoiceJob | None:
        """Record an error message and mark the job as failed.

        Args:
            job_id: UUID of the voice job.
            error: Description of the failure.

        Returns:
            The updated VoiceJob, or ``None`` if not found.
        """
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.error = error
        job.status = "failed"
        await self._session.flush()
        await self._session.refresh(job)
        return job
