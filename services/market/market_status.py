# services/market/market_status.py
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
    Now includes a 15-minute buffer for the closing auction.
    """
    import pandas as pd
    try:
        now_market = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    except:
        return True
    
    if now_market.weekday() not in MARKET_WEEKDAYS:
        return False
    
    current_time = now_market.time()
    start_time = pd.Timestamp("10:00:00").time()
    end_time   = pd.Timestamp("16:15:00").time()
    
    return start_time <= current_time <= end_time


def market_badge() -> html.Span:
    """Render market status badge."""
    open_ = is_market_open()
    return html.Span(
        "Open" if open_ else "Closed",
        id="market-badge",
        className=f"market-badge {'badge-open' if open_ else 'badge-closed'}",
    )
