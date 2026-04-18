"""
core/cache.py
=============
Simple TTL-based in-memory cache with expiration.

Added: history_fingerprint() — stable SHA-256 hash of the transaction list
used as part of the portfolio cache key to detect when history has changed.
"""

import hashlib
import json
import time

from config.settings import CACHE_TTL_SECONDS


_CACHE: dict = {}


def get_cache(key: str):
    """Return cached value if present and not expired, else None."""
    entry = _CACHE.get(key)
    if not entry:
        return None
    value, expiry = entry
    if time.time() > expiry:
        del _CACHE[key]
        return None
    return value


def set_cache(key: str, value, ttl: int | None = None) -> None:
    """
    Store value under key with a TTL in seconds.

    If ttl is None, uses CACHE_TTL_SECONDS from config (configurable via env var).
    """
    if ttl is None:
        ttl = CACHE_TTL_SECONDS
    _CACHE[key] = (value, time.time() + ttl)


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