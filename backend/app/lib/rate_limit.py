"""Lightweight fixed-window rate limiter backed by Redis.

Used to bound expensive/external-call endpoints (e.g. the AI assistant,
which proxies to a paid LLM API) per-user, so a single account cannot
exhaust quota or drive up cost through rapid repeated requests.

This is intentionally simple (fixed window, not sliding/token-bucket) to
keep the failure mode obvious and the implementation auditable. Redis is
already a hard dependency of this project (Celery broker / OAuth state),
so this adds no new infrastructure requirement.
"""

from __future__ import annotations

import redis.asyncio as redis


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s.")


async def enforce_rate_limit(
    client: redis.Redis,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise RateLimitExceeded if `key` has been hit more than `limit` times
    in the current `window_seconds` window. Fails open (allows the request)
    if Redis is unreachable, so a Redis outage degrades rate limiting rather
    than taking down the feature entirely.
    """

    redis_key = f"ratelimit:{key}"
    try:
        current = await client.incr(redis_key)
        if current == 1:
            await client.expire(redis_key, window_seconds)
        if current > limit:
            ttl = await client.ttl(redis_key)
            retry_after = ttl if ttl and ttl > 0 else window_seconds
            raise RateLimitExceeded(retry_after_seconds=retry_after)
    except RateLimitExceeded:
        raise
    except Exception:  # noqa: BLE001 - fail open on infra errors, never block on our own outage
        return
