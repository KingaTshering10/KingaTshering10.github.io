"""Sliding-window rate limiter.

Default backend is in-process (single node). ``RateLimiterBackend`` is the
adapter seam for a Redis implementation in multi-node deployments — see
docs/DEPLOYMENT.md for the replacement steps.
"""

import time
from collections import defaultdict, deque
from typing import Protocol

from app.core.errors import RateLimitedError


class RateLimiterBackend(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a hit; return True when the caller is within the limit."""
        ...


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        cutoff = now - window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter: InMemoryRateLimiter = InMemoryRateLimiter()


def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    if not rate_limiter.hit(key, limit, window_seconds):
        raise RateLimitedError("Too many attempts. Please wait and try again.", code="RATE_LIMITED")
