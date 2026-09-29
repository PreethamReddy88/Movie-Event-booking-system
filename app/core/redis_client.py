"""Async Redis client (or in-memory fake for local dev).

When REDIS_URL is set to "fake", uses a simple dict-based mock
that implements the same SET NX / GET / DELETE interface.
This lets you run the full app without a Redis server.
"""

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class FakeRedis:
    """In-memory Redis mock for local development.

    Supports the subset of commands used by the booking service:
    SET (with NX and EX), GET, DELETE, PING.
    """

    def __init__(self):
        self._store: dict = {}

    async def set(self, key: str, value: str, nx: bool = False, ex: int = None) -> bool:
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self._store.clear()


# ── Client initialization ──
if settings.REDIS_URL == "fake":
    logger.info("Using FakeRedis (in-memory) — set REDIS_URL for real Redis")
    redis_client = FakeRedis()
else:
    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )


async def ping_redis() -> None:
    """Verify Redis connectivity (called on startup)."""
    await redis_client.ping()


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    await redis_client.aclose()
