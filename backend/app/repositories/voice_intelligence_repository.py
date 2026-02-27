"""Repository for VoiceIntelligence database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_intelligence import VoiceIntelligence


class VoiceIntelligenceRepository:
    """Encapsulates all database access for the VoiceIntelligence model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_intelligence_record(
        self, record: VoiceIntelligence
    ) -> VoiceIntelligence:
        """Persist a new VoiceIntelligence record.

        Args:
            record: A fully populated VoiceIntelligence ORM instance.

        Returns:
            The persisted record with server-generated fields populated.
        """
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_by_job_id(self, voice_job_id: UUID) -> VoiceIntelligence | None:
        """Fetch a VoiceIntelligence record by its parent voice job id.

        Args:
            voice_job_id: UUID of the associated VoiceJob.

        Returns:
            The VoiceIntelligence record if found, otherwise ``None``.
        """
        stmt = select(VoiceIntelligence).where(
            VoiceIntelligence.voice_job_id == voice_job_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_action_executed(self, record_id: UUID) -> None:
        """Set the action_executed flag to True for idempotency.

        Args:
            record_id: UUID primary key of the VoiceIntelligence record.
        """
        stmt = select(VoiceIntelligence).where(VoiceIntelligence.id == record_id)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is not None:
            record.action_executed = True
            await self._session.flush()
