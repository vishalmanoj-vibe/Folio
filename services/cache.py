import time

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


def set_cache(key: str, value, ttl: int = 60) -> None:
    """Store value under key with a TTL in seconds."""
    _CACHE[key] = (value, time.time() + ttl)


def bust_cache(key: str) -> None:
    """Explicitly remove a cache entry."""
    _CACHE.pop(key, None)
