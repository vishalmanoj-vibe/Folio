# core/__init__.py
"""
Core utilities for Folio.

Cache, validators, and custom exceptions.
"""

from core.cache import _CACHE as _cache
from core.cache import bust_cache, cache_stats, evict_expired, get_cache, set_cache
from core.exceptions import (
    DataHandlerError,
    MarketDataError,
    ValidationError,
)
from core.validators import validate_transaction

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
