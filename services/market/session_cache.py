import os
import json
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_filename():
    # Use Sydney time for the filename to ensure consistency
    today = pd.Timestamp.now(tz="Australia/Sydney").strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, f"intraday_{today}.json")

def record_snapshot(enriched_holdings: list[dict]):
    """
    Record the current price for all holdings into today's session cache.
    
    This persistence layer ensures that the "Today" (1d) chart remains 
    continuous even if the application is restarted during trading hours.
    
    Timezone Strategy:
    - We strictly use 'Australia/Sydney' for timestamps to align with ASX market sessions.
    - Prices are only recorded if they differ from the last entry to prevent file bloat.
    """
    filename = _get_filename()
    session_data = {}
    
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                session_data = json.load(f)
        except Exception as e:
            logger.warning("Failed to read session cache: %s", e)

    # Use Sydney time for the recorded timestamp
    now_str = pd.Timestamp.now(tz="Australia/Sydney").strftime("%Y-%m-%d %H:%M:%S")
    updated = False
    
    for h in enriched_holdings:
        ticker = h["ticker"]
        price = h["last_price"]
        
        # Don't record if price is 0 (fetch failure)
        if price <= 0:
            continue
            
        if ticker not in session_data:
            session_data[ticker] = []
            
        # Only add if the price is different (avoid bloat)
        history = session_data[ticker]
        if not history or history[-1]["Close"] != price:
            history.append({"Date": now_str, "Close": price})
            updated = True
            
    if updated:
        try:
            with open(filename, "w") as f:
                json.dump(session_data, f)
        except Exception as e:
            logger.error("Failed to write session cache: %s", e)

def get_session_history(ticker: str) -> pd.Series:
    """
    Retrieve today's recorded points for a ticker as a pandas Series.
    """
    filename = _get_filename()
    if not os.path.exists(filename):
        return pd.Series(dtype=float)
        
    try:
        with open(filename, "r") as f:
            session_data = json.load(f)
        
        history = session_data.get(ticker, [])
        if not history:
            return pd.Series(dtype=float)
            
        df = pd.DataFrame(history)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df["Close"]
    except Exception as e:
        logger.warning("Failed to read session history for %s: %s", ticker, e)
        return pd.Series(dtype=float)

def clear_old_caches(keep_days: int = 7):
    """Delete session caches older than keep_days."""
    # Use Sydney time for cutoff calculation
    cutoff = pd.Timestamp.now(tz="Australia/Sydney") - pd.Timedelta(days=keep_days)
    
    for f in os.listdir(CACHE_DIR):
        if not f.startswith("intraday_"):
            continue
        try:
            date_str = f.replace("intraday_", "").replace(".json", "")
            f_date = datetime.strptime(date_str, "%Y-%m-%d")
            # Convert f_date to Sydney for comparison if needed, or just compare dates
            if pd.Timestamp(f_date).date() < cutoff.date():
                os.remove(os.path.join(CACHE_DIR, f))
                logger.info("Cleared old session cache: %s", f)
        except Exception as e:
            logger.warning("Failed to clear cache %s: %s", f, e)
