"""Repository for VoiceLog database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_log import VoiceLog


class VoiceRepository:
    """Encapsulates all database access for the VoiceLog model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, voice_log: VoiceLog) -> VoiceLog:
        """Persist a new VoiceLog.

        Args:
            voice_log: A fully populated VoiceLog ORM instance.

        Returns:
            The persisted VoiceLog with server-generated fields populated.
        """
        self._session.add(voice_log)
        await self._session.flush()
        await self._session.refresh(voice_log)
        return voice_log

    async def get_by_id(self, log_id: UUID) -> VoiceLog | None:
        """Fetch a single voice log by primary key.

        Args:
            log_id: UUID of the voice log.

        Returns:
            The VoiceLog if found, otherwise ``None``.
        """
        stmt = select(VoiceLog).where(VoiceLog.id == log_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[VoiceLog]:
        """Return all voice logs for a user, most recent first.

        Args:
            user_id: UUID of the owning user.

        Returns:
            List of VoiceLog instances.
        """
        stmt = (
            select(VoiceLog)
            .where(VoiceLog.user_id == user_id)
            .order_by(VoiceLog.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
