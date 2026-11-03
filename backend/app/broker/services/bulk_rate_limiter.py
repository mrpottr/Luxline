"""Process-local sliding-window limiter for broker bulk operations."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class InMemoryBulkRateLimiter:
    """Thread-safe fallback limiter; deployments with multiple workers need a shared adapter."""

    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def consume(self, key: str, *, maximum: int, window_seconds: int) -> bool:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= maximum:
                return False
            events.append(now)
            return True
