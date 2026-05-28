# core/cache.py
"""
core/cache.py
=============
Simple TTL-based in-memory cache with expiration.

Added: history_fingerprint() — stable SHA-256 hash of the transaction list
used as part of the portfolio cache key to detect when history has changed.
"""

import hashlib
import json
import sys
import threading
import time

from config.settings import CACHE_TTL_SECONDS

MAX_CACHE_ENTRIES = 200
MAX_CACHE_MEMORY_MB = 100

_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_WRITE_COUNTER = 0
_CACHE_HITS = 0
_CACHE_MISSES = 0


def cache_stats() -> dict:
    """Return metrics about the current cache state."""
    total_mb = 0.0
    oldest_age = 0.0
    now = time.time()

    with _CACHE_LOCK:
        if _CACHE:
            try:
                # Optimized: skip deep memory checks for performance
                total_bytes = sys.getsizeof(_CACHE)
                total_mb = total_bytes / (1024 * 1024)
            except Exception:
                total_mb = 0.0

            oldest_entry = min(_CACHE.values(), key=lambda x: x[2])
            oldest_age = now - oldest_entry[2]

        total_requests = _CACHE_HITS + _CACHE_MISSES
        hit_ratio = (_CACHE_HITS / total_requests) if total_requests > 0 else 0.0

    return {
        "entries": len(_CACHE),
        "memory_mb": round(total_mb, 2),
        "oldest_age_sec": round(oldest_age, 2),
        "hit_ratio": round(hit_ratio, 2),
    }


def evict_expired() -> None:
    """Remove all expired entries from the cache. Called within lock."""
    now = time.time()
    expired_keys = [k for k, v in _CACHE.items() if now > v[1]]
    for k in expired_keys:
        del _CACHE[k]


def get_cache(key: str):
    """Return cached value if present and not expired, else None."""
    global _CACHE_HITS, _CACHE_MISSES
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            _CACHE_MISSES += 1
            return None
        value, expiry, inserted_at = entry
        if time.time() > expiry:
            del _CACHE[key]
            _CACHE_MISSES += 1
            return None
        _CACHE_HITS += 1
        return value


def set_cache(key: str, value, ttl: int | None = None) -> None:
    """
    Store value under key with a TTL in seconds.
    """
    global _WRITE_COUNTER
    if ttl is None:
        ttl = CACHE_TTL_SECONDS

    with _CACHE_LOCK:
        _WRITE_COUNTER += 1
        if _WRITE_COUNTER >= 100:
            evict_expired()
            _WRITE_COUNTER = 0

        if len(_CACHE) >= MAX_CACHE_ENTRIES:
            # First pass: remove expired
            evict_expired()

            # Second pass: remove oldest if still over limit
            if len(_CACHE) >= MAX_CACHE_ENTRIES:
                target_size = int(MAX_CACHE_ENTRIES * 0.8)
                sorted_keys = sorted(_CACHE.keys(), key=lambda k: _CACHE[k][2])
                keys_to_remove = len(_CACHE) - target_size
                for i in range(keys_to_remove):
                    _CACHE.pop(sorted_keys[i], None)

        _CACHE[key] = (value, time.time() + ttl, time.time())


def bust_cache(key: str) -> None:
    """Explicitly remove a cache entry."""
    _CACHE.pop(key, None)


def history_fingerprint(history: list[dict]) -> str:
    """
    Return a stable 16-char hex digest that uniquely identifies a transaction list.

    The list is sorted by (date, ticker, type) before hashing so that order
    differences in the raw list don't produce spurious cache misses.
    Cheap to compute — no network calls, no pandas.
    """
    if not history:
        return "empty"

    try:
        canonical = sorted(
            history,
            key=lambda t: (
                str(t.get("date", "")),
                str(t.get("ticker", "")),
                str(t.get("type", "")),
                str(t.get("shares", "")),
                str(t.get("price", "")),
            ),
        )
        payload = json.dumps(canonical, sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()[:16]
    except Exception:
        # Fallback: length + sum of share counts (never crashes)
        return f"len{len(history)}"
