# services/market/market_status.py
"""
Market status service.

Checks if market is open based on timezone, weekdays, and hours.
"""

import pandas as pd
from config.settings import MARKET_TIMEZONE, MARKET_WEEKDAYS

def is_market_open() -> bool:
    """
    Check if market is open based on configured timezone, weekdays, and hours.
    Now includes a 15-minute buffer for the closing auction.
    
    NOTE: MARKET_HOURS = (10, 16) in settings does not reflect the 16:15 
    post-auction buffer hardcoded here. We keep the hardcoded strings 
    for precision.
    """
    try:
        now_market = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    except Exception:
        # Fallback if timezone conversion fails
        return True
    
    if now_market.weekday() not in MARKET_WEEKDAYS:
        return False
    
    current_time = now_market.time()
    # NOTE: MARKET_HOURS from config.settings is defined as (10, 16) and is intentionally
    # not used here. The closing time is set to 16:15 (not 16:00) to include the ASX
    # closing auction window. Updating MARKET_HOURS to reflect this would require changing
    # its type from a simple int tuple to support fractional hours, which is out of scope.
    # If you need to adjust market hours, edit the hardcoded timestamps below directly.
    start_time = pd.Timestamp("10:00:00").time()
    end_time   = pd.Timestamp("16:15:00").time()
    
    return start_time <= current_time <= end_time
