import asyncio
import logging
import time
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis Client
_redis_client: Optional[aioredis.Redis] = None
_redis_checked: bool = False

# In-memory fallbacks when Redis is not available (useful during local test runs)
_memory_store = {}


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Returns singleton async Redis client or None if connection fails."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.1,
            socket_timeout=0.1
        )
        await asyncio.wait_for(client.ping(), timeout=0.1)
        _redis_client = client
    except Exception:
        _redis_client = None

    _redis_checked = True
    return _redis_client


class TokenRevocationService:
    """Manages revoked JWT tokens and session blacklist."""

    @staticmethod
    async def revoke_token(token_hash: str, expire_seconds: int = 604800) -> None:
        client = await get_redis_client()
        key = f"revoked_token:{token_hash}"
        if client:
            await client.setex(key, expire_seconds, "1")
        else:
            _memory_store[key] = time.time() + expire_seconds

    @staticmethod
    async def is_token_revoked(token_hash: str) -> bool:
        client = await get_redis_client()
        key = f"revoked_token:{token_hash}"
        if client:
            return await client.exists(key) > 0
        expire = _memory_store.get(key)
        if expire:
            if time.time() < expire:
                return True
            else:
                del _memory_store[key]
        return False


class LockoutService:
    """Tracks failed login attempts and handles lockout policy."""

    @staticmethod
    async def record_failed_attempt(email: str) -> int:
        """Increments failed attempt count and returns current failures count."""
        key = f"login_fails:{email.lower()}"
        client = await get_redis_client()
        window_seconds = settings.LOCKOUT_WINDOW_MINUTES * 60
        if client:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            count = results[0]
        else:
            now = time.time()
            data = _memory_store.get(key, {"count": 0, "expires": now + window_seconds})
            if now > data["expires"]:
                data = {"count": 0, "expires": now + window_seconds}
            data["count"] += 1
            _memory_store[key] = data
            count = data["count"]

        if count >= settings.LOCKOUT_THRESHOLD:
            # Set lockout flag
            lock_key = f"account_locked:{email.lower()}"
            lock_duration = settings.LOCKOUT_DURATION_MINUTES * 60
            if client:
                await client.setex(lock_key, lock_duration, "1")
            else:
                _memory_store[lock_key] = time.time() + lock_duration
        return count

    @staticmethod
    async def is_locked(email: str) -> bool:
        """Checks if account is locked due to too many failed attempts."""
        lock_key = f"account_locked:{email.lower()}"
        client = await get_redis_client()
        if client:
            return await client.exists(lock_key) > 0
        expire = _memory_store.get(lock_key)
        if expire:
            if time.time() < expire:
                return True
            else:
                del _memory_store[lock_key]
        return False

    @staticmethod
    async def reset_failed_attempts(email: str) -> None:
        """Resets failed attempt count on successful login."""
        fail_key = f"login_fails:{email.lower()}"
        lock_key = f"account_locked:{email.lower()}"
        client = await get_redis_client()
        if client:
            await client.delete(fail_key, lock_key)
        else:
            _memory_store.pop(fail_key, None)
            _memory_store.pop(lock_key, None)

