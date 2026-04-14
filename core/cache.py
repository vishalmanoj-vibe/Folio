"""
Cache management for Portfolio Dashboard.

Simple TTL-based in-memory cache with expiration.
"""

import time
from config.settings import CACHE_TTL_SECONDS


_CACHE: dict = {}


def get_cache(key: str):
    """
    Return cached value if present and not expired, else None.
    """
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
