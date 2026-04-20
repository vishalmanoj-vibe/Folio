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
    """
    now = pd.Timestamp.now()
    mapping = {
        "1d":  now.replace(hour=10, minute=0, second=0, microsecond=0),
        "1mo": now - timedelta(days=30),
        "3mo": now - timedelta(days=91),
        "6mo": now - timedelta(days=182),
        "1y":  now - timedelta(days=365),
        "2y":  now - timedelta(days=730),
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
