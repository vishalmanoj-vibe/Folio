# services/market/market_status.py
"""
Market status service.

Checks if market is open based on timezone, weekdays, and hours.
"""

import pandas as pd
import holidays
from config.settings import MARKET_TIMEZONE, MARKET_WEEKDAYS

# ASX observes NSW public holidays
au_holidays = holidays.AU(prov='NSW')

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
        
    if now_market.date() in au_holidays:
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

def time_until_market_open() -> float:
    """
    Returns the number of seconds until the next 09:55 AM on a trading day (Mon-Fri).
    If currently between 09:55 and 16:15 on a weekday, returns 0.
    Handles DST transitions correctly by building timezone-aware timestamps.
    """
    now = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    
    today_target = pd.Timestamp(
        year=now.year, month=now.month, day=now.day,
        hour=9, minute=55, second=0, tz=MARKET_TIMEZONE
    )
    
    if now.weekday() in MARKET_WEEKDAYS and now.date() not in au_holidays:
        if now < today_target:
            return (today_target - now).total_seconds()
        elif now.time() <= pd.Timestamp("16:15:00").time():
            return 0.0
            
    # Find next weekday
    next_day = now + pd.DateOffset(days=1)
    while next_day.weekday() not in MARKET_WEEKDAYS or next_day.date() in au_holidays:
        next_day += pd.DateOffset(days=1)
        
    next_target = pd.Timestamp(
        year=next_day.year, month=next_day.month, day=next_day.day,
        hour=9, minute=55, second=0, tz=MARKET_TIMEZONE
    )
    
    return (next_target - now).total_seconds()
