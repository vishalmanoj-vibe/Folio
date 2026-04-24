# config/__init__.py
"""
Configuration package for Portfolio Dashboard.

Exports all settings, constants, and logging configuration.
Maintains backward compatibility with existing imports.
"""

from config.settings import (
    SCRIPT_DIR,
    CSV_PATH,
    REFRESH_INTERVAL,
    MARKET_TIMEZONE,
    MARKET_WEEKDAYS,
    MARKET_HOURS,
    API_MAX_RETRIES,
    API_RETRY_BACKOFF_BASE,
    CACHE_TTL_SECONDS,
    ALERT_THRESHOLDS,
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
    "CSV_PATH",
    "REFRESH_INTERVAL",
    "MARKET_TIMEZONE",
    "MARKET_WEEKDAYS",
    "MARKET_HOURS",
    "API_MAX_RETRIES",
    "API_RETRY_BACKOFF_BASE",
    "CACHE_TTL_SECONDS",
    "ALERT_THRESHOLDS",
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
