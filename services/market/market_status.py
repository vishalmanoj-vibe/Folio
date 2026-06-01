# services/market/market_status.py
"""
Market status service.

Checks if market is open based on timezone, weekdays, and hours.
"""

import holidays
import pandas as pd

from config.settings import MARKET_TIMEZONE, MARKET_WEEKDAYS

# ASX observes NSW public holidays
au_holidays = holidays.AU(prov="NSW")


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


def get_previous_trading_session_start(relative_to: pd.Timestamp | None = None) -> pd.Timestamp:
    """
    Finds the start time (15:00) of the previous trading session relative to today or a given base date.
    Skips weekends automatically.
    Used for providing context on 1d charts.
    """
    if relative_to is None:
        relative_to = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    else:
        # Ensure it has the correct timezone
        if relative_to.tzinfo is None:
            relative_to = relative_to.tz_localize(MARKET_TIMEZONE)
        else:
            relative_to = relative_to.tz_convert(MARKET_TIMEZONE)

    today = relative_to.floor("D")

    # Start looking from yesterday
    prev_day = today - pd.Timedelta(days=1)

    # Skip weekends and holidays
    while prev_day.weekday() not in MARKET_WEEKDAYS or prev_day.date() in au_holidays:
        prev_day -= pd.Timedelta(days=1)

    return prev_day.replace(hour=15, minute=0, second=0, microsecond=0)


def get_effective_session_context() -> dict:
    """
    Determines the "Effective Session" date and the "Comparison Anchor" date.

    If Market is Open:
        Effective: Today
        Anchor: Yesterday (Previous Trading Day)
    If Market is Closed (After hours):
        Effective: Today
        Anchor: Yesterday (Previous Trading Day)
    If Market is Closed (Weekend or Before Open):
        Effective: Most recent trading day (e.g. Friday)
        Anchor: Day before that (e.g. Thursday)

    Returns:
        dict: {
            'effective_date': pd.Timestamp (normalized),
            'anchor_date': pd.Timestamp (normalized),
            'is_live': bool (True if today is the effective session)
        }
    """
    now = pd.Timestamp.now(tz=MARKET_TIMEZONE)
    today = now.normalize()

    def is_trading_day(dt):
        return dt.weekday() in MARKET_WEEKDAYS and dt.date() not in au_holidays

    # Case 1: It is a trading day
    if is_trading_day(now):
        # If it's before 10am, we are still looking at the previous session's results as the "effective" ones
        if now.hour < 10:
            effective = today - pd.Timedelta(days=1)
            while not is_trading_day(effective):
                effective -= pd.Timedelta(days=1)

            anchor = effective - pd.Timedelta(days=1)
            while not is_trading_day(anchor):
                anchor -= pd.Timedelta(days=1)

            return {"effective_date": effective, "anchor_date": anchor, "is_live": False}
        else:
            # Market is open or after hours on a trading day
            anchor = today - pd.Timedelta(days=1)
            while not is_trading_day(anchor):
                anchor -= pd.Timedelta(days=1)

            return {"effective_date": today, "anchor_date": anchor, "is_live": True}

    # Case 2: Weekend or Holiday
    effective = today - pd.Timedelta(days=1)
    while not is_trading_day(effective):
        effective -= pd.Timedelta(days=1)

    anchor = effective - pd.Timedelta(days=1)
    while not is_trading_day(anchor):
        anchor -= pd.Timedelta(days=1)

    return {"effective_date": effective, "anchor_date": anchor, "is_live": False}


def time_until_market_open() -> float:
    """
    Returns the number of seconds until the next 09:55 AM on a trading day (Mon-Fri).
    If currently between 09:55 and 16:15 on a weekday, returns 0.
    Handles DST transitions correctly by building timezone-aware timestamps.
    """
    now = pd.Timestamp.now(tz=MARKET_TIMEZONE)

    today_target = pd.Timestamp(
        year=now.year, month=now.month, day=now.day, hour=9, minute=55, second=0, tz=MARKET_TIMEZONE
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
        year=next_day.year,
        month=next_day.month,
        day=next_day.day,
        hour=9,
        minute=55,
        second=0,
        tz=MARKET_TIMEZONE,
    )

    return (next_target - now).total_seconds()
