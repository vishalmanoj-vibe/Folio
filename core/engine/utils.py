# core/engine/utils.py
"""
core/engine/utils.py
====================
Shared utilities for date handling, timezones, and calculations.
"""

import pandas as pd
from datetime import timedelta

def get_period_cutoff(period: str) -> pd.Timestamp | None:
    """
    Calculate the start date based on a given time period string.
    If a Timestamp or date object is passed, return it as a pd.Timestamp.
    """
    import datetime
    if isinstance(period, (pd.Timestamp, datetime.date, datetime.datetime)):
        return pd.Timestamp(period)
    # We align cutoffs with the UTC-normalized indices from fetch_live.
    # For ASX, 'Today' start (10:00 AM Sydney) is 00:00 UTC.
    # We use a robust way to get this regardless of server local time.
    try:
        now_syd = pd.Timestamp.now(tz="Australia/Sydney")
    except Exception:
        # Fallback if tzdata is missing (though rare on Mac/Linux)
        now_syd = pd.Timestamp.now()

    now_utc = now_syd.tz_convert("UTC").tz_localize(None)
    
    mapping = {
        "1d":  now_utc.floor("D"),
        "1mo": now_utc - timedelta(days=30),
        "3mo": now_utc - timedelta(days=91),
        "6mo": now_utc - timedelta(days=182),
        "ytd": pd.Timestamp(year=now_syd.year, month=1, day=1),
        "1y":  now_utc - timedelta(days=365),
        "2y":  now_utc - timedelta(days=730),
        "5y":  now_utc - timedelta(days=1825),
        "max": None,
    }
    return mapping.get(period, None)

def normalise_tz(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Strip timezone from a DatetimeIndex so comparisons with tz-naive values work."""
    if index.tz is not None:
        return index.tz_convert("UTC").tz_localize(None)
    return index

def fmt_date_index(index: pd.DatetimeIndex) -> list[str]:
    """Format a DatetimeIndex into YYYY-MM-DD strings."""
    return [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in index]
