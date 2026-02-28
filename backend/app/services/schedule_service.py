"""Service layer for ScheduleBlock business logic."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.schedule_block import ScheduleBlock
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.schedule_schema import (
    ScheduleBlockCreate,
    ScheduleBlockListResponse,
    ScheduleBlockResponse,
)

logger = get_logger(__name__)


class ScheduleService:
    """Orchestrates schedule block creation and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ScheduleRepository(session)

    async def create_block(
        self, user_id: UUID, payload: ScheduleBlockCreate
    ) -> ScheduleBlockResponse:
        """Create a new schedule block.

        Args:
            user_id: The authenticated user's UUID.
            payload: Validated schedule block data.

        Returns:
            The created block as a response schema.
        """
        block = ScheduleBlock(
            user_id=user_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            block_type=payload.block_type,
        )
        block = await self._repo.create(block)
        logger.info("schedule_block_created", block_id=str(block.id), user_id=str(user_id))
        return ScheduleBlockResponse.model_validate(block)

    async def list_blocks(self, user_id: UUID) -> ScheduleBlockListResponse:
        """Return all schedule blocks for the given user.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A list wrapper with count.
        """
        blocks = await self._repo.list_by_user(user_id)
        items = [ScheduleBlockResponse.model_validate(b) for b in blocks]
        return ScheduleBlockListResponse(blocks=items, count=len(items))

    async def delete_block(self, user_id: UUID, block_id: UUID) -> None:
        """Delete a schedule block owned by the given user.

        Args:
            user_id: The authenticated user's UUID.
            block_id: The block to delete.

        Raises:
            ValueError: If the block does not exist or belongs to another user.
        """
        block = await self._repo.get_by_id(block_id)
        if block is None or block.user_id != user_id:
            raise ValueError("Block not found")
        await self._repo.delete(block)
        logger.info("schedule_block_deleted", block_id=str(block_id), user_id=str(user_id))
