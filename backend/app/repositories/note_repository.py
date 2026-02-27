"""Repository for Note database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NoteRepository:
    """Encapsulates all database access for the Note model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_note(self, note: Note) -> Note:
        """Persist a new Note to the database.

        Args:
            note: A fully populated Note ORM instance.

        Returns:
            The persisted Note with server-generated fields populated.
        """
        self._session.add(note)
        await self._session.flush()
        await self._session.refresh(note)
        return note

    async def get_notes_for_user(self, user_id: UUID) -> list[Note]:
        """Fetch all notes for a given user, ordered newest first.

        Args:
            user_id: UUID of the user.

        Returns:
            A list of Note records.
        """
        stmt = (
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
