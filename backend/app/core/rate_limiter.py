import time
from fastapi import Request, HTTPException, status
from app.core.redis import get_redis_client, _memory_store


class RateLimiter:
    """Sliding-window rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        # Forwarded-For header support if behind proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        endpoint = request.url.path
        key = f"rate_limit:{client_ip}:{endpoint}"
        now = time.time()
        window = 60  # 1 minute

        client = await get_redis_client()
        if client:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            count = results[2]
        else:
            timestamps = _memory_store.get(key, [])
            timestamps = [t for t in timestamps if t > now - window]
            timestamps.append(now)
            _memory_store[key] = timestamps
            count = len(timestamps)

        if count > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute allowed."
            )


# Predefined rate limiters
login_rate_limiter = RateLimiter(requests_per_minute=5)
general_rate_limiter = RateLimiter(requests_per_minute=100)

