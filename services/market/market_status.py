"""
Market status service.

Checks if market is open based on timezone, weekdays, and hours.
"""

from datetime import datetime
import pytz
from dash import html
from config.settings import MARKET_TIMEZONE, MARKET_WEEKDAYS, MARKET_HOURS
from config.constants import SURFACE, BORDER, GREEN, T_SEC


def is_market_open() -> bool:
    """
    Check if market is open based on configured timezone, weekdays, and hours.
    
    Configuration can be overridden via environment variables:
      - MARKET_TIMEZONE: Default "Australia/Sydney"
      - Market hours: Monday-Friday, 10:00-16:00 (configurable)
    """
    now_utc = datetime.now(pytz.utc)
    now_market = now_utc.astimezone(pytz.timezone(MARKET_TIMEZONE))
    
    is_weekday = now_market.weekday() in MARKET_WEEKDAYS
    hour_start, hour_end = MARKET_HOURS
    is_trading_hours = hour_start <= now_market.hour < hour_end
    
    return is_weekday and is_trading_hours


def market_badge() -> html.Span:
    """Render market status badge."""
    open_ = is_market_open()
    return html.Span(
        "ASX open" if open_ else "ASX closed",
        className=f"badge {'badge-open' if open_ else 'badge-closed'}",
    )
