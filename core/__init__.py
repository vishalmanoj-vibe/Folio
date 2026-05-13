# core/__init__.py
"""
Core utilities for Folio.

Cache, validators, and custom exceptions.
"""

from core.cache import get_cache, set_cache, bust_cache, cache_stats, evict_expired, _CACHE as _cache
from core.validators import validate_transaction
from core.exceptions import (
    ValidationError,
    DataHandlerError,
    MarketDataError,
)

__all__ = [
    # Cache
    "get_cache",
    "set_cache",
    "bust_cache",
    "cache_stats",
    "evict_expired",
    "_cache",
    # Validators
    "validate_transaction",
    # Exceptions
    "ValidationError",
    "DataHandlerError",
    "MarketDataError",
]
