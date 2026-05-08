# config/settings.py
"""
Settings and configuration for Portfolio Dashboard.

All environment variables with sensible defaults are defined here.
Easily customizable via .env file.
"""

import os

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CACHE_DIR = os.path.join(SCRIPT_DIR, "data", "cache")

CSV_PATH = os.getenv(
    "PORTFOLIO_CSV",
    os.path.join(SCRIPT_DIR, "data", "raw", "stock_portfolio_transactions.csv")
)
METADATA_CSV_PATH = os.getenv(
    "METADATA_CSV",
    os.path.join(DATA_CACHE_DIR, "etf_metadata_cache.csv")
)
WATCHLIST_CSV_PATH = os.getenv(
    "WATCHLIST_CSV",
    os.path.join(SCRIPT_DIR, "data", "raw", "watchlist.csv")
)

# ── Intervals ─────────────────────────────────────────────────────────────────
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_MS", 300_000))  # 5 minutes in ms
TECHNICALS_CACHE_TTL = int(os.getenv("TECHNICALS_CACHE_TTL", 86400))  # 24 hours in seconds
DIVIDENDS_CACHE_TTL = int(os.getenv("DIVIDENDS_CACHE_TTL", 604800))   # 7 days in seconds

# ── Market configuration ──────────────────────────────────────────────────────
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "Australia/Sydney")
MARKET_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
MARKET_HOURS = (10, 16)             # 10:00-16:00

# ── API retry configuration ───────────────────────────────────────────────────
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", 3))
API_RETRY_BACKOFF_BASE = float(os.getenv("API_RETRY_BACKOFF_BASE", 2.0))

# ── Cache configuration ───────────────────────────────────────────────────────
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 25))

# ── Alert thresholds ─────────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    "individual_drawdown": float(os.getenv("ALERT_INDIVIDUAL_DRAWDOWN_PCT", -20.0)),
    "portfolio_drawdown": float(os.getenv("ALERT_PORTFOLIO_DRAWDOWN_PCT", -15.0)),
}
