# config/__init__.py
"""
Configuration package for Folio.

Exports all settings, constants, and logging configuration.
Maintains backward compatibility with existing imports.
"""

from config.constants import (
    BG,
    BORDER,
    CHART_INFO,
    COLORS,
    GREEN,
    NAMES,
    PLOTLY_BASE,
    RED,
    SURFACE,
    T_PRI,
    T_SEC,
    get_theme,
)
from config.logging import CONFIG as LOGGING_CONFIG
from config.logging import setup_logging
from config.settings import (
    ALERT_THRESHOLDS,
    API_MAX_RETRIES,
    API_RETRY_BACKOFF_BASE,
    CACHE_TTL_SECONDS,
    DB_PATH,
    DIVIDENDS_CACHE_TTL,
    MARKET_HOURS,
    MARKET_TIMEZONE,
    MARKET_WEEKDAYS,
    REFRESH_INTERVAL,
    SCRIPT_DIR,
    TECHNICALS_CACHE_TTL,
)

__all__ = [
    # Settings
    "SCRIPT_DIR",
    "DB_PATH",
    "REFRESH_INTERVAL",
    "MARKET_TIMEZONE",
    "MARKET_WEEKDAYS",
    "MARKET_HOURS",
    "API_MAX_RETRIES",
    "API_RETRY_BACKOFF_BASE",
    "CACHE_TTL_SECONDS",
    "ALERT_THRESHOLDS",
    "TECHNICALS_CACHE_TTL",
    "DIVIDENDS_CACHE_TTL",
    # Constants
    "BG",
    "SURFACE",
    "BORDER",
    "T_PRI",
    "T_SEC",
    "GREEN",
    "RED",
    "COLORS",
    "PLOTLY_BASE",
    "get_theme",
    "NAMES",
    "CHART_INFO",
    # Logging
    "setup_logging",
    "LOGGING_CONFIG",
]
