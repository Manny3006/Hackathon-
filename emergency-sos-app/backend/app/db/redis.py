import redis.asyncio as redis
from app.core.config import settings


# Redis client for async operations
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    """Dependency to get Redis client."""
    return redis_client


async def init_redis():
    """Initialize Redis connection."""
    await redis_client.ping()


async def close_redis():
    """Close Redis connection."""
    await redis_client.close()
