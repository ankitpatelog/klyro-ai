from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    yield request.app.state.redis
