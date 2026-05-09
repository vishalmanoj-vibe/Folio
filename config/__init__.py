# config/__init__.py
"""
Configuration package for Folio.

Exports all settings, constants, and logging configuration.
Maintains backward compatibility with existing imports.
"""

from config.settings import (
    SCRIPT_DIR,
    DB_PATH,
    REFRESH_INTERVAL,
    MARKET_TIMEZONE,
    MARKET_WEEKDAYS,
    MARKET_HOURS,
    API_MAX_RETRIES,
    API_RETRY_BACKOFF_BASE,
    CACHE_TTL_SECONDS,
    ALERT_THRESHOLDS,
    TECHNICALS_CACHE_TTL,
    DIVIDENDS_CACHE_TTL,
)

from config.constants import (
    BG,
    SURFACE,
    BORDER,
    T_PRI,
    T_SEC,
    GREEN,
    RED,
    COLORS,
    PLOTLY_BASE,
    get_theme,
    NAMES,
    CHART_INFO,
)

from config.logging import setup_logging, CONFIG as LOGGING_CONFIG

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
