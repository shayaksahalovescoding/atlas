import time
import threading
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    def __init__(self, max_size=1000, ttl_seconds=300):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                ts = self._timestamps.get(key, 0)
                if time.time() - ts > self._ttl:
                    del self._cache[key]
                    del self._timestamps[key]
                    self._misses += 1
                    return None
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            self._timestamps[key] = time.time()
            while len(self._cache) > self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._timestamps.pop(oldest_key, None)

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def get_stats(self):
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
        }
