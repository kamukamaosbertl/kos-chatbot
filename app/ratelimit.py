"""Simple in-memory rate limit per visitor IP, so nobody can burn through your AI credits."""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 300):
        self.max = max_requests
        self.window = window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        if len(self.hits) > 10_000:          # keep memory small on free hosting
            for k in [k for k, v in self.hits.items() if not v][:5000]:
                del self.hits[k]
        return True
