"""In-process sliding-window rate limiter.

Enough for a single API process. Running several replicas would need a shared
store (Redis) behind the same `hit()` interface.
"""

import time
from collections import deque
from threading import Lock

from app.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry = max(1, int(hits[0] + self.window - now) + 1)
                raise RateLimited("Too many attempts. Try again shortly.", headers={"Retry-After": str(retry)})
            hits.append(now)
            if len(self._hits) > 10_000:  # drop idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= now - self.window]:
                    del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Credentials endpoints: per client IP and per submitted email.
login_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
register_limiter = SlidingWindowLimiter(limit=5, window_seconds=60)
refresh_limiter = SlidingWindowLimiter(limit=30, window_seconds=60)
# Writes that create rows (quests, invites, parties) per user.
write_limiter = SlidingWindowLimiter(limit=120, window_seconds=60)

ALL_LIMITERS = (login_limiter, register_limiter, refresh_limiter, write_limiter)
