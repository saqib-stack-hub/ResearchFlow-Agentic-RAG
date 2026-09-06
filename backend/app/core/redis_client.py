"""
ResearchFlow AI — Redis Client
Connection pool with helpers for caching and pub/sub.
"""
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings


_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


async def set_cache(key: str, value: Any, ttl: int = None) -> None:
    """Set a value in Redis cache with optional TTL."""
    r = await get_redis()
    ttl = ttl or settings.REDIS_TTL
    serialized = json.dumps(value) if not isinstance(value, str) else value
    await r.setex(key, ttl, serialized)


async def get_cache(key: str) -> Optional[Any]:
    """Get a value from Redis cache."""
    r = await get_redis()
    value = await r.get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


async def delete_cache(key: str) -> None:
    """Delete a key from Redis cache."""
    r = await get_redis()
    await r.delete(key)


async def set_document_status(document_id: str, status: dict) -> None:
    """Track document processing status in Redis."""
    key = f"doc_status:{document_id}"
    await set_cache(key, status, ttl=86400)  # 24 hours


async def get_document_status(document_id: str) -> Optional[dict]:
    """Get document processing status from Redis."""
    key = f"doc_status:{document_id}"
    return await get_cache(key)


async def check_redis_health() -> bool:
    """Check if Redis connection is healthy."""
    try:
        r = await get_redis()
        await r.ping()
        return True
    except Exception:
        return False


async def increment_rate_limit(key: str, window: int) -> int:
    """Increment rate limit counter and return current count."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = await pipe.execute()
    return results[0]
