"""Async Redis client and voice job queue operations."""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

VOICE_JOBS_QUEUE: str = "voice_jobs"

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return a shared async Redis connection, creating it on first call.

    Returns:
        An ``aioredis.Redis`` client backed by a connection pool.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info("redis_pool_created", url=settings.redis_url)
    return _redis_pool


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("redis_pool_closed")


async def enqueue_voice_job(job_id: str) -> None:
    """Push a voice job identifier onto the processing queue.

    Args:
        job_id: The string representation of the job UUID.
    """
    client = await get_redis()
    await client.lpush(VOICE_JOBS_QUEUE, job_id)
    logger.info("voice_job_enqueued", job_id=job_id)


async def dequeue_voice_job() -> Optional[str]:
    """Pop the next voice job identifier from the queue.

    Uses ``brpop`` with a 2-second timeout so the worker can
    periodically check for shutdown signals.

    Returns:
        The job UUID string, or ``None`` if the queue is empty after the timeout.
    """
    client = await get_redis()
    result = await client.brpop(VOICE_JOBS_QUEUE, timeout=2)
    if result is not None:
        # brpop returns (queue_name, value)
        return result[1]
    return None
