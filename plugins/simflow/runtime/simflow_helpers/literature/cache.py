"""TTL + LRU cache for literature/structure API queries."""

import time
from collections import OrderedDict
from typing import Any, Optional


class TTLCache:
    """In-memory cache with TTL (time-to-live) and LRU eviction."""

    def __init__(self, max_size: int = 256, ttl_seconds: float = 900):
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: dict = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Returns None if missing or expired."""
        if key not in self._cache:
            return None

        # Check TTL
        if time.time() - self._timestamps[key] > self._ttl:
            self._evict(key)
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            self._cache[key] = value
        self._timestamps[key] = time.time()

    def delete(self, key: str) -> None:
        """Remove key from cache."""
        self._evict(key)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._timestamps.clear()

    def _evict(self, key: str) -> None:
        """Remove a specific key."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def _evict_oldest(self) -> None:
        """Remove the least recently used entry."""
        if self._cache:
            oldest_key, _ = self._cache.popitem(last=False)
            self._timestamps.pop(oldest_key, None)

    @property
    def size(self) -> int:
        return len(self._cache)
