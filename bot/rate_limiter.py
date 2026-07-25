import asyncio
import time
from collections import deque


class RateLimiter:
    """Per-user rate limiter: max 10 messages per minute per user."""

    def __init__(self, max_per_minute: int = 10):
        self._max = max_per_minute
        self._data: dict[int, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def can_send(self, user_id: int) -> bool:
        async with self._lock:
            self._prune(user_id)
            records = self._data.get(user_id, None)
            if records is None:
                return True
            return len(records) < self._max

    async def record_send(self, user_id: int) -> None:
        async with self._lock:
            self._prune(user_id)
            records = self._data.setdefault(user_id, deque())
            records.append(time.time())

    async def get_wait_time(self, user_id: int) -> float:
        async with self._lock:
            self._prune(user_id)
            records = self._data.get(user_id, None)
            if records is None or len(records) < self._max:
                return 0.0
            oldest = records[0]
            wait = 60.0 - (time.time() - oldest)
            return max(0.0, wait)

    def _prune(self, user_id: int) -> None:
        records = self._data.get(user_id, None)
        if records is None:
            return
        cutoff = time.time() - 60.0
        while records and records[0] < cutoff:
            records.popleft()
        if not records:
            del self._data[user_id]
