from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings

REDIS_SOCKET_TIMEOUT = 10

def create_redis_client() -> Redis:
    # Add socket_timeout for connection and blocking commands
    return Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
    )

async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    yield request.app.state.redis
