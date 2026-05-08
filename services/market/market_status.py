# services/market/market_status.py
"""
Market status service.

Checks if market is open based on timezone, weekdays, and hours.
"""

import pandas as pd
from config.settings import MARKET_TIMEZONE, MARKET_WEEKDAYS

def is_market_open(include_auction: bool = True) -> bool:
    """
    Determines if the market is currently in an active trading or processing window.
    """
    try:
        now_market = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    except Exception:
        return True
    
    if now_market.weekday() not in MARKET_WEEKDAYS:
        return False
    
    current_time = now_market.time()
    start_time = pd.Timestamp("10:00:00").time()
    end_time_str = "16:15:00" if include_auction else "16:00:00"
    end_time = pd.Timestamp(end_time_str).time()
    
    return start_time <= current_time <= end_time

def get_previous_trading_session_start() -> pd.Timestamp:
    """
    Finds the start time (15:00) of the previous trading session relative to today.
    Skips weekends automatically.
    """
    now_syd = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    today = now_syd.floor("D")
    
    # Start looking from yesterday
    prev_day = today - pd.Timedelta(days=1)
    
    # Skip weekends (MARKET_WEEKDAYS is [0,1,2,3,4])
    while prev_day.weekday() not in MARKET_WEEKDAYS:
        prev_day -= pd.Timedelta(days=1)
        
    return prev_day.replace(hour=15, minute=0, second=0, microsecond=0)
