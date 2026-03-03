import redis.asyncio as redis

from app.config import get_settings

_redis_client = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def cache_get(key: str) -> str | None:
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    r = await get_redis()
    await r.set(key, value, ex=ttl)
