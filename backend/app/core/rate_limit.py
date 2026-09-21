from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.errors import AppError
from app.core.redis import get_redis


class RateLimitExceededError(AppError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            "Too many requests, please try again later",
            code="rate_limited",
            status_code=429,
            headers={"Retry-After": str(retry_after_seconds)},
        )


def rate_limiter(scope: str, limit: int, window_seconds: int):
    """Fixed-window rate limit, keyed per client IP + scope, backed by a
    Redis INCR/EXPIRE counter (reuses the same Redis instance as caching --
    no new infrastructure). Returns a FastAPI dependency; attach it to a
    route via `dependencies=[Depends(rate_limiter("scope", limit, window))]`.

    Fixed windows can allow a short burst around the window boundary (e.g.
    two limit-sized bursts a few seconds apart, near the reset). That's an
    acceptable tradeoff here for the simplicity of a single INCR+EXPIRE
    round trip -- a sliding-window log would need more Redis calls per
    request for a guarantee this project doesn't need.
    """

    async def _check(request: Request, redis: Redis = Depends(get_redis)) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{scope}:{client_ip}"

        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)

        if count > limit:
            ttl = await redis.ttl(key)
            raise RateLimitExceededError(retry_after_seconds=max(ttl, 1))

    return _check
