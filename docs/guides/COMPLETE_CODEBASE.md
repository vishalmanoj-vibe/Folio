# Portfolio Dashboard - Complete Codebase

This document contains the complete source code for the Portfolio Dashboard project, organized by file path and structure.

## Project Structure
```
portfolio_dashboard/
├── app.py                          # Main application entry point
├── config/                         # Configuration package
│   ├── __init__.py                 # Config package exports
│   ├── settings.py                 # Environment variables & settings
│   ├── constants.py                # UI constants, colors, themes
│   └── logging.py                  # Logging configuration
├── core/                           # Core utilities package
│   ├── __init__.py                 # Core package exports
│   ├── cache.py                    # TTL caching implementation
│   ├── validators.py               # Input validation functions
│   └── exceptions.py               # Custom exception classes
├── models/                         # Data models package
│   ├── __init__.py                 # Models package exports
│   └── transaction.py              # TypedDict data models
├── services/                       # Business logic services
│   ├── __init__.py                 # Services package exports
│   ├── alerts.py                   # Alert checking logic
│   └── market/                     # Market data services
│       ├── __init__.py             # Market package exports
│       ├── fetcher.py              # Live market data fetching
│       └── status.py               # Market status checking
├── pages/                          # Dash page components
│   ├── portfolio.py                # Main portfolio page
│   └── etf_detail.py               # ETF detail page
├── callbacks/                      # Dash callback functions
│   ├── core_callbacks.py           # Main data refresh callbacks
│   ├── transaction_callbacks.py    # Transaction management callbacks
│   ├── chart_callbacks.py          # Chart rendering callbacks
│   ├── alert_callbacks.py          # Alert display callbacks
│   └── ui_callbacks.py             # UI interaction callbacks
├── components/                     # Reusable UI components
│   ├── layout.py                   # Main layout and styling
│   └── ui_helpers.py               # UI helper functions
├── data/                           # Data processing layer
│   ├── csv_handler.py              # CSV file operations
│   └── portfolio_builder.py        # Portfolio aggregation logic
├── test/                           # Test suite
│   ├── __init__.py                 # Test package
│   ├── integration/                # Integration tests
│   │   └── __init__.py
│   ├── test_alert_service.py       # Alert service tests
│   ├── test_csv_handler.py         # CSV handler tests
│   ├── test_market_status.py       # Market status tests
│   └── test_portfolio_builder.py   # Portfolio builder tests
└── utils/                          # Utility functions
```

---

## Source Code

### app.py
```python
"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /             → pages/portfolio.py   (existing dashboard, unchanged)
  /etf/<ticker> → pages/etf_detail.py  (new ETF drill-down)

File layout:
  app.py                          ← this file
  config/                         ← settings, constants, logging setup
  core/                           ← validators, cache, exceptions
  models/                         ← TypedDict data models
  data/
    csv_handler.py                ← load_csv / save_csv
    portfolio_builder.py          ← build_holdings
  services/
    alerts.py                     ← check_alerts
    market/
      fetcher.py                  ← fetch_live (yfinance)
      status.py                   ← is_market_open / market_badge
  components/
    layout.py                     ← portfolio page layout tree
    ui_helpers.py                 ← stat_card, chart_title, section, txn_table
  callbacks/
    core_callbacks.py             ← refresh, stat cards, live table  (+ ticker links)
    transaction_callbacks.py      ← add_transaction, txn log
    chart_callbacks.py            ← all 7 charts + ticker toggle buttons
    alert_callbacks.py            ← alerts banner
    ui_callbacks.py               ← theme toggle, PDF print (clientside)
  pages/
    portfolio.py                  ← Dash page wrapper: /
    etf_detail.py                 ← Dash page wrapper: /etf/<ticker>  ← NEW
"""

# Setup logging first, before any other imports
from config.logging import setup_logging
setup_logging()

import dash
from dash import html, dcc

from components.layout import INDEX_STRING
from data.csv_handler import load_csv
from config.settings import REFRESH_INTERVAL

import callbacks.core_callbacks         as core
import callbacks.transaction_callbacks  as txn
import callbacks.chart_callbacks        as charts
import callbacks.alert_callbacks        as alerts
import callbacks.ui_callbacks           as ui

# ── Load initial CSV data ─────────────────────────────────────────────────────
INITIAL_HISTORY: list[dict] = []
try:
    INITIAL_HISTORY = load_csv()
except Exception as e:
    print(f"\nERROR loading CSV:\n{e}")
    print("Dashboard will start with an empty portfolio.\n")

# ── Dash app (Pages enabled) ──────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)
app.title        = "Portfolio — Live"
app.index_string = INDEX_STRING

# pages/* imported HERE — after dash.Dash() — so register_page() succeeds
import pages.etf_detail as etf_detail  # noqa: E402

# ── Root layout ───────────────────────────────────────────────────────────────
# Shared stores + interval live here so they survive page navigation.
# Each page renders its own chrome inside dash.page_container.
app.layout = html.Div(
    [
        dcc.Store(id="txn-store",        data=INITIAL_HISTORY),
        dcc.Store(id="portfolio-store"),
        dcc.Store(id="alerts-store"),
        dcc.Store(id="theme-store",      data="dark"),
        dcc.Interval(id="live-interval", interval=REFRESH_INTERVAL, n_intervals=0),

        dash.page_container,
    ],
    style={
        "fontFamily":      "system-ui,-apple-system,sans-serif",
        "color":           "var(--t-pri)",
        "maxWidth":        "1300px",
        "margin":          "0 auto",
        "backgroundColor": "var(--bg)",
    },
)

# ── Register callbacks ────────────────────────────────────────────────────────
core.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)
etf_detail.register_callbacks(app)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config.settings import CSV_PATH
    print(f"\n  Portfolio Dashboard — Live P&L  (multi-page)")
    print(f"  CSV:        {CSV_PATH}")
    print(f"  Portfolio:  http://127.0.0.1:8050/")
    print(f"  ETF detail: http://127.0.0.1:8050/etf/VHY\n")
    app.run(debug=False, port=8050)
```

### config/__init__.py
```python
"""
Configuration package for Portfolio Dashboard.

Exports all settings, constants, and logging configuration.
Maintains backward compatibility with existing imports.
"""

from config.settings import (
    SCRIPT_DIR,
    CSV_PATH,
    REFRESH_INTERVAL,
    MARKET_TIMEZONE,
    MARKET_WEEKDAYS,
    MARKET_HOURS,
    API_MAX_RETRIES,
    API_RETRY_BACKOFF_BASE,
    CACHE_TTL_SECONDS,
    ALERT_THRESHOLDS,
)

from config.constants import (
    BG,
    SURFACE,
    BORDER,
    T_PRI,
    T_SEC,
    GREEN,
    RED,
    COLORS,
    PLOTLY_BASE,
    get_theme,
    NAMES,
    CHART_INFO,
)

from config.logging import setup_logging, CONFIG as LOGGING_CONFIG

__all__ = [
    # Settings
    "SCRIPT_DIR",
    "CSV_PATH",
    "REFRESH_INTERVAL",
    "MARKET_TIMEZONE",
    "MARKET_WEEKDAYS",
    "MARKET_HOURS",
    "API_MAX_RETRIES",
    "API_RETRY_BACKOFF_BASE",
    "CACHE_TTL_SECONDS",
    "ALERT_THRESHOLDS",
    # Constants
    "BG",
    "SURFACE",
    "BORDER",
    "T_PRI",
    "T_SEC",
    "GREEN",
    "RED",
    "COLORS",
    "PLOTLY_BASE",
    "get_theme",
    "NAMES",
    "CHART_INFO",
    # Logging
    "setup_logging",
    "LOGGING_CONFIG",
]
```

### config/settings.py
```python
"""
Settings and configuration for Portfolio Dashboard.

All environment variables with sensible defaults are defined here.
Easily customizable via .env file.
"""

import os

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.getenv(
    "PORTFOLIO_CSV",
    os.path.join(SCRIPT_DIR, "data", "raw", "stock_portfolio_transactions.csv")
)

# ── Intervals ─────────────────────────────────────────────────────────────────
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_MS", 60_000))  # milliseconds

# ── Market configuration ──────────────────────────────────────────────────────
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "Australia/Sydney")
MARKET_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
MARKET_HOURS = (10, 16)             # 10:00-16:00

# ── API retry configuration ───────────────────────────────────────────────────
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", 3))
API_RETRY_BACKOFF_BASE = float(os.getenv("API_RETRY_BACKOFF_BASE", 2.0))

# ── Cache configuration ───────────────────────────────────────────────────────
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 60))

# ── Alert thresholds ─────────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    "individual_drawdown": float(os.getenv("ALERT_INDIVIDUAL_DRAWDOWN_PCT", -20.0)),
    "portfolio_drawdown": float(os.getenv("ALERT_PORTFOLIO_DRAWDOWN_PCT", -15.0)),
}
```

### config/constants.py
```python
"""
Constants for Portfolio Dashboard.

Colors, theme definitions, ETF names, and chart information.
"""

# ── Dark theme tokens (defaults) ──────────────────────────────────────────────
BG      = "#111110"
SURFACE = "#1c1c1a"
BORDER  = "rgba(255,255,255,0.08)"
T_PRI   = "#f0ede8"
T_SEC   = "#8a8880"
GREEN   = "#1D9E75"
RED     = "#E24B4A"

COLORS = [
    "#378ADD", "#1D9E75", "#EF9F27", "#D85A30",
    "#7F77DD", "#D4537E", "#639922", "#5DCAA5",
    "#FAC775", "#85B7EB", "#F0997B", "#AFA9EC",
]

PLOTLY_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)

# ── Theme-aware style resolver ────────────────────────────────────────────────
def get_theme(theme: str) -> dict:
    """
    Return a dict of colour tokens and a PLOTLY_BASE for the given theme.
    Usage:  t = get_theme(theme);  t["BG"], t["PLOTLY_BASE"], ...
    """
    if theme == "light":
        bg      = "#ffffff"
        surface = "#f4f4f2"
        border  = "rgba(0,0,0,0.09)"
        t_pri   = "#1a1a1a"
        t_sec   = "#6b6b67"
    else:  # dark (default)
        bg      = "#111110"
        surface = "#1c1c1a"
        border  = "rgba(255,255,255,0.08)"
        t_pri   = "#f0ede8"
        t_sec   = "#8a8880"

    return {
        "BG":      bg,
        "SURFACE": surface,
        "BORDER":  border,
        "T_PRI":   t_pri,
        "T_SEC":   t_sec,
        "PLOTLY_BASE": dict(
            paper_bgcolor=bg,
            plot_bgcolor=surface,
            font=dict(family="system-ui,sans-serif", color=t_pri, size=13),
            margin=dict(l=16, r=16, t=40, b=16),
            legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        ),
    }

# ── ETF display names ─────────────────────────────────────────────────────────
NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
}

# ── Chart tooltip copy ────────────────────────────────────────────────────────
CHART_INFO = {
    "pnl-history": (
        "P&L from purchase date",
        "Shows your profit or loss since you bought each holding. The line starts "
        "at $0 on your purchase date and moves up (profit) or down (loss) as the "
        "price changes. Toggle between Portfolio (combined) or individual stocks. "
        "Switch between $ and % using the P&L view dropdown."
    ),
    "price-chart": (
        "Normalised price history",
        "All holdings are rescaled to start at 100 so you can compare performance "
        "side by side regardless of actual price. A line at 120 means that holding "
        "is up 20% over the selected period. The dotted line at 100 is the baseline."
    ),
    "allocation": (
        "Portfolio allocation",
        "Shows what % of your total portfolio value each holding represents today. "
        "Larger slices = bigger positions. Use this to check if you are "
        "over-concentrated in any single ETF."
    ),
    "pnl-bar": (
        "Unrealised P&L — all time",
        "The dollar (or %) gain or loss on each holding since you first bought it, "
        "based on your weighted average purchase price. Green = profitable, "
        "Red = at a loss. Unrealised — only becomes real when you sell."
    ),
    "day-pnl": (
        "Today's P&L",
        "How much each holding gained or lost today vs yesterday's closing price. "
        "Resets every trading day. Green = up today, red = down today."
    ),
    "dividend": (
        "Annual dividend income",
        "Estimated annual dividend income from each holding based on dividends paid "
        "over the last 12 months, scaled to your share count. "
        "Yield % = annual dividends divided by current market value."
    ),
    "correlation": (
        "Return correlation matrix",
        "How similarly two holdings move together, from -1 to +1. Near +1 (green) "
        "= move together, less diversification. Near 0 = move independently. "
        "Near -1 (red) = move oppositely, good diversification."
    ),
}
```

### config/logging.py
```python
"""
Logging configuration for Portfolio Dashboard.

Centralized logging with console and file handlers.
Configure via environment variables:
  - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
  - LOG_FILE: Path to log file (default: portfolio.log in script dir)
  - LOG_FILE_ENABLED: true/false to enable file logging (default: true)
"""

import logging.config
import os
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", os.path.join(SCRIPT_DIR, "portfolio.log"))
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"

# Create handlers list dynamically
handlers_list = ["console"]
if LOG_FILE_ENABLED:
    handlers_list.append("file")

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)-8s] %(name)-20s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_FILE,
            "formatter": "standard",
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "level": LOG_LEVEL,
            "handlers": handlers_list,
            "propagate": True,
        },
        # Suppress noisy third-party loggers
        "yfinance": {
            "level": "WARNING",
        },
        "urllib3": {
            "level": "WARNING",
        },
        "dash": {
            "level": "INFO",
        },
    },
}


def setup_logging():
    """Initialize logging configuration."""
    logging.config.dictConfig(CONFIG)
    logger = logging.getLogger(__name__)
    
    if LOG_FILE_ENABLED:
        logger.info(f"Logging configured: console={LOG_LEVEL}, file={LOG_FILE}")
    else:
        logger.info(f"Logging configured: console={LOG_LEVEL} (file logging disabled)")
```

### core/__init__.py
```python
"""
Core utilities for Portfolio Dashboard.

Cache, validators, and custom exceptions.
"""

from core.cache import get_cache, set_cache, bust_cache
from core.validators import validate_transaction
from core.exceptions import (
    ValidationError,
    DataHandlerError,
    MarketDataError,
)

__all__ = [
    # Cache
    "get_cache",
    "set_cache",
    "bust_cache",
    # Validators
    "validate_transaction",
    # Exceptions
    "ValidationError",
    "DataHandlerError",
    "MarketDataError",
]
```

### core/cache.py
```python
"""
Cache management for Portfolio Dashboard.

Simple TTL-based in-memory cache with expiration.
"""

import time
from config.settings import CACHE_TTL_SECONDS


_CACHE: dict = {}


def get_cache(key: str):
    """
    Return cached value if present and not expired, else None.
    """
    entry = _CACHE.get(key)
    if not entry:
        return None
    value, expiry = entry
    if time.time() > expiry:
        del _CACHE[key]
        return None
    return value


def set_cache(key: str, value, ttl: int | None = None) -> None:
    """
    Store value under key with a TTL in seconds.
    
    If ttl is None, uses CACHE_TTL_SECONDS from config (configurable via env var).
    """
    if ttl is None:
        ttl = CACHE_TTL_SECONDS
    _CACHE[key] = (value, time.time() + ttl)


def bust_cache(key: str) -> None:
    """Explicitly remove a cache entry."""
    _CACHE.pop(key, None)
```

### core/validators.py
```python
"""
Validators for Portfolio Dashboard.

Transaction validation and data checking utilities.
"""

import pandas as pd


def validate_transaction(txn: dict) -> tuple[bool, str]:
    """
    Validate transaction structure before aggregation.
    
    Args:
        txn: Transaction dictionary with keys: type, ticker, shares, price, date
    
    Returns:
        (is_valid, error_message)
    """
    required_keys = ["type", "ticker", "shares", "price", "date"]
    missing = [k for k in required_keys if k not in txn]
    if missing:
        return False, f"Transaction missing keys: {missing}"
    
    # Validate types
    try:
        shares = float(txn["shares"])
        price = float(txn["price"])
    except (TypeError, ValueError):
        return False, "Shares and price must be numeric"
    
    if shares <= 0 or price <= 0:
        return False, "Shares and price must be positive"
    
    txn_type = str(txn.get("type", "buy")).lower().strip()
    if txn_type not in ["buy", "sell"]:
        return False, f"Type must be 'buy' or 'sell', got '{txn_type}'"
    
    # Validate date format
    try:
        pd.to_datetime(str(txn["date"]), format="%Y-%m-%d")
    except (ValueError, TypeError):
        return False, f"Date must be YYYY-MM-DD, got '{txn['date']}'"
    
    return True, ""
```

### core/exceptions.py
```python
"""
Custom exceptions for Portfolio Dashboard.

Domain-specific exceptions for better error handling.
"""


class PortfolioDashboardError(Exception):
    """Base exception for Portfolio Dashboard."""
    pass


class ValidationError(PortfolioDashboardError):
    """Raised when data validation fails."""
    pass


class DataHandlerError(PortfolioDashboardError):
    """Raised when CSV I/O operation fails."""
    pass


class MarketDataError(PortfolioDashboardError):
    """Raised when market data fetching fails."""
    pass


class ConfigurationError(PortfolioDashboardError):
    """Raised when configuration is invalid."""
    pass
```

### models/__init__.py
```python
"""
Portfolio models for Portfolio Dashboard.

Portfolio and aggregated holding structures.
"""

from typing import TypedDict
from models.transaction import EnrichedHolding, Transaction


class Portfolio(TypedDict):
    """Aggregated portfolio snapshot."""
    holdings: list[EnrichedHolding]
    histories: dict  # {ticker: [price records]}
    fetched_at: str  # Time of last fetch
    total_value: float | None  # Optional: total portfolio value
    total_cost: float | None  # Optional: total cost basis
    total_pnl: float | None  # Optional: total profit/loss
```

### models/transaction.py
```python
"""
Data models for Portfolio Dashboard.

Type definitions and data schemas.
"""

from typing import TypedDict
from datetime import datetime


class Transaction(TypedDict):
    """Transaction data structure."""
    type: str      # 'buy' or 'sell'
    ticker: str    # ETF ticker (without .AX)
    shares: float  # Number of shares
    price: float   # Price per share
    date: str      # YYYY-MM-DD format


class TransactionRecord(Transaction):
    """Full transaction record with metadata."""
    id: str | None  # Optional transaction ID
    created_at: datetime | None  # Optional timestamp


class BuyTranche(TypedDict):
    """Individual buy tranche for P&L tracking."""
    ticker: str
    shares: float
    price: float
    date: str
    buy_price: float
    buy_date: str


class Holding(TypedDict):
    """Portfolio holding."""
    ticker: str
    ticker_yf: str  # With .AX suffix
    name: str
    market: str
    total_shares: float
    total_cost: float
    avg_cost: float
    first_purchase: str  # YYYY-MM-DD
    buy_tranches: list[BuyTranche]


class EnrichedHolding(Holding):
    """Holding with market data enrichment."""
    last_price: float
    prev_close: float
    day_high: float
    day_low: float
    day_chg: float
    day_chg_pct: float
    day_pnl: float
    mkt_value: float
    pnl: float
    pnl_pct: float
    total_div: float
    annual_div: float
    div_yield: float
    tranches: list[dict]
```

### services/__init__.py
```python
"""
Services layer for Portfolio Dashboard.

Business logic for market data, alerts, and portfolio operations.
"""

from services.market import fetch_live, is_market_open, market_badge
from services.alerts import check_alerts

__all__ = [
    "fetch_live",
    "is_market_open",
    "market_badge",
    "check_alerts",
]  
```

### services/alerts.py
```python
"""
Alert service for Portfolio Dashboard.

Detects portfolio and position drawdown conditions.
"""

from config.settings import ALERT_THRESHOLDS


def check_alerts(holdings: list[dict], thresholds: dict | None = None) -> list[dict]:
    """
    Scan enriched holdings for alert conditions.

    Configuration:
      - individual_drawdown: Alert if any holding down X% all-time (default -20%)
      - portfolio_drawdown:  Alert if portfolio down X% all-time (default -15%)

    Thresholds can be overridden via config.ALERT_THRESHOLDS or environment variables:
      - ALERT_INDIVIDUAL_DRAWDOWN_PCT
      - ALERT_PORTFOLIO_DRAWDOWN_PCT

    Returns a list of alert dicts: {type, ticker?, message}
    """
    if thresholds is None:
        thresholds = ALERT_THRESHOLDS

    alerts: list[dict] = []
    individual_threshold = thresholds.get("individual_drawdown", -20.0)
    portfolio_threshold = thresholds.get("portfolio_drawdown", -15.0)

    # Individual position drawdowns
    for h in holdings:
        if h.get("pnl_pct", 0) <= individual_threshold:
            alerts.append({
                "type":    "drawdown",
                "ticker":  h["ticker"],
                "message": f"{h['ticker']} down {h['pnl_pct']:.2f}% since purchase",
            })

    # Portfolio total drawdown
    total_cost  = sum(h.get("total_cost", 0) for h in holdings)
    total_value = sum(h.get("mkt_value",  0) for h in holdings)

    if total_cost > 0:
        total_pct = (total_value - total_cost) / total_cost * 100
        if total_pct <= portfolio_threshold:
            alerts.append({
                "type":    "portfolio",
                "message": f"Portfolio down {total_pct:.2f}% overall",
            })

    return alerts
```

### services/market/__init__.py
```python
"""
Market services for Portfolio Dashboard.

Market data fetching and status checking.
"""

from services.market.fetcher import fetch_live, _download_with_retry
from services.market.status import is_market_open, market_badge

__all__ = [
    "fetch_live",
    "_download_with_retry",
    "is_market_open",
    "market_badge",
]
```

### services/market/fetcher.py
```python
"""
Market data fetching service.

Fetches live prices, history, dividends, and P&L from yfinance.
Includes retry logic and caching.
"""

import logging
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from core import get_cache, set_cache
from config.settings import API_MAX_RETRIES, API_RETRY_BACKOFF_BASE, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)


def _download_with_retry(
    tickers: str,
    period: str,
    max_retries: int = API_MAX_RETRIES,
    backoff_base: float = API_RETRY_BACKOFF_BASE,
) -> pd.DataFrame:
    """
    Download data from yfinance with exponential backoff retry logic.
    
    Args:
        tickers: Space-separated ticker symbols (e.g., "VHY.AX VAS.AX")
        period: yfinance period string (e.g., "3mo", "max", "1y")
        max_retries: Maximum number of retry attempts
        backoff_base: Base for exponential backoff (delay = backoff_base ^ attempt)
    
    Returns:
        DataFrame on success, empty DataFrame on failure after all retries
    """
    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers,
                period=period,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
            )
            logger.debug(f"Download succeeded for {len(tickers.split()) if isinstance(tickers, str) else len(tickers)} tickers, period={period}")
            return df
        except Exception as e:
            is_last_attempt = attempt == max_retries - 1
            if is_last_attempt:
                logger.warning(
                    f"Download failed after {max_retries} attempts (period={period}): {e}"
                )
                return pd.DataFrame()
            else:
                # Exponential backoff
                delay = backoff_base ** attempt
                logger.debug(
                    f"Download attempt {attempt + 1}/{max_retries} failed, retrying in {delay}s (period={period}): {e}"
                )
                time.sleep(delay)


def _extract_close(bulk_df: pd.DataFrame, ticker_yf: str) -> pd.Series:
    """
    Safely pull a single ticker's Close series from a yf.download() result.

    yfinance MultiIndex layout varies by version and ticker count:
      - Single ticker              → flat columns ['Close', 'Open', ...]
      - Multi, group_by='ticker'  → MultiIndex (ticker, field)
      - Multi, group_by='column'  → MultiIndex (field, ticker)
    We try all layouts and return empty Series rather than crash.
    """
    if bulk_df is None or bulk_df.empty:
        return pd.Series(dtype=float)

    cols = bulk_df.columns

    if not isinstance(cols, pd.MultiIndex):
        # Flat — single ticker download
        return bulk_df["Close"].dropna() if "Close" in cols else pd.Series(dtype=float)

    # Layout A: (ticker, field)
    if (ticker_yf, "Close") in cols:
        return bulk_df[(ticker_yf, "Close")].dropna()
    # Layout B: (field, ticker)
    if ("Close", ticker_yf) in cols:
        return bulk_df[("Close", ticker_yf)].dropna()
    # Layout C: base ticker without exchange suffix
    base = ticker_yf.split(".")[0]
    if (base, "Close") in cols:
        return bulk_df[(base, "Close")].dropna()
    if ("Close", base) in cols:
        return bulk_df[("Close", base)].dropna()

    logger.warning("No Close column for %s — cols sample: %s", ticker_yf, list(cols[:6]))
    return pd.Series(dtype=float)


def fetch_live(holdings: list[dict], hist_period: str = "3mo") -> dict:
    """
    Fetch live prices, history, dividends and per-tranche P&L for all holdings.

    Strategy:
      - yf.download() × 2  (period + max) for all tickers at once — fast
      - yf.Ticker.fast_info per ticker for intraday quote during market hours
      - yf.Ticker.history per ticker for dividends (only column download drops)
      - Historical close used as price fallback when market is closed
    """
    if not holdings:
        return {}

    cache_key = f"market_data_{hist_period}"
    cached = get_cache(cache_key)
    if cached:
        logger.debug("Cache hit for period=%s", hist_period)
        return cached

    tickers_yf  = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(tickers_yf)
    logger.info("Fetching %s  period=%s", tickers_yf, hist_period)

    # ── Bulk downloads with retry logic (auto_adjust=False preserves Dividends column) ──
    multi_period = _download_with_retry(tickers_str, period=hist_period)
    multi_full = _download_with_retry(tickers_str, period="max")

    enriched:  list[dict] = []
    histories: dict        = {}

    for h in holdings:
        ticker    = h["ticker"]
        ticker_yf = h["ticker_yf"]
        try:
            # ── Extract history series ────────────────────────────────────────
            close_period = _extract_close(multi_period, ticker_yf)
            close_full   = _extract_close(multi_full,   ticker_yf)

            # Normalise index to tz-naive datetime
            if not close_period.empty:
                close_period.index = pd.to_datetime(close_period.index).tz_localize(None)
            if not close_full.empty:
                close_full.index = pd.to_datetime(close_full.index).tz_localize(None)

            # ── Period history → normalised price chart ───────────────────────
            if not close_period.empty:
                df_p = close_period.reset_index()
                df_p.columns = ["Date", "Close"]
                histories[ticker] = df_p.to_dict("records")

            # ── Price: fast_info (intraday) with historical close as fallback ──
            # fast_info returns 0.0 outside market hours — guard with > 0
            tk = yf.Ticker(ticker_yf)
            fi = tk.fast_info

            fi_last  = fi.get("last_price")      or 0.0
            fi_prev  = fi.get("previous_close")  or 0.0
            fi_high  = fi.get("day_high")        or 0.0
            fi_low   = fi.get("day_low")         or 0.0

            # Use last two rows of full history for reliable closed-market prices
            hist_last  = float(close_full.iloc[-1])  if len(close_full) >= 1 else None
            hist_prev  = float(close_full.iloc[-2])  if len(close_full) >= 2 else None

            last_price = float(fi_last if fi_last > 0 else (hist_last or h["avg_cost"]))
            prev_close = float(fi_prev if fi_prev > 0 else (hist_prev or last_price))
            day_high   = float(fi_high if fi_high > 0 else last_price)
            day_low    = float(fi_low  if fi_low  > 0 else last_price)

            logger.info(
                "%-6s  fi_last=%6.3f  hist_last=%s  hist_prev=%s  using_last=%.3f  using_prev=%.3f",
                ticker,
                fi_last,
                f"{hist_last:.3f}" if hist_last else "N/A",
                f"{hist_prev:.3f}" if hist_prev else "N/A",
                last_price,
                prev_close,
            )

            # ── Derived day + portfolio metrics ───────────────────────────────
            day_chg     = round(last_price - prev_close, 4)
            day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)
            mkt_value   = round(h["total_shares"] * last_price, 2)
            pnl         = round(mkt_value - h["total_cost"], 2)
            pnl_pct     = round((pnl / h["total_cost"] * 100) if h["total_cost"] else 0, 2)
            day_pnl     = round(day_chg * h["total_shares"], 2)

            # ── Dividends (needs individual Ticker — bulk drops this column) ──
            try:
                hist_raw = tk.history(period="max", auto_adjust=False)
                div_s = (
                    hist_raw["Dividends"]
                    if not hist_raw.empty and "Dividends" in hist_raw.columns
                    else pd.Series(dtype=float)
                )
            except Exception:
                div_s = pd.Series(dtype=float)

            cutoff     = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            annual_div = round(float(div_s[div_s.index >= cutoff].sum()) * h["total_shares"], 2)
            total_div  = round(float(div_s.sum()) * h["total_shares"], 2)
            div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0, 2)

            # ── Per-tranche P&L history ───────────────────────────────────────
            tranche_data: list[dict] = []
            if not close_full.empty:
                for tr in h.get("buy_tranches", []):
                    buy_date = pd.to_datetime(tr["date"])
                    mask = close_full.index >= buy_date
                    if not mask.any():
                        logger.debug("%s tranche %s: no history after buy date", ticker, tr["date"])
                        continue
                    sub   = close_full[mask].copy()
                    pnl_s = (sub - tr["price"]) * tr["shares"]
                    pct_s = (sub - tr["price"]) / tr["price"] * 100
                    tranche_data.append({
                        "dates":     [d.strftime("%Y-%m-%d") for d in sub.index],
                        "pnl":       [round(v, 2) for v in pnl_s.tolist()],
                        "pct":       [round(v, 2) for v in pct_s.tolist()],
                        "shares":    float(tr["shares"]),
                        "buy_price": float(tr["price"]),
                        "buy_date":  tr["date"],
                    })
            else:
                logger.warning("%s: close_full empty — no P&L tranche data", ticker)

            logger.info(
                "%-6s  pnl=%+.2f (%+.2f%%)  day=%+.2f  tranches=%d",
                ticker, pnl, pnl_pct, day_pnl, len(tranche_data),
            )

            enriched.append({
                **h,
                "last_price":  round(last_price, 3),
                "prev_close":  round(prev_close, 3),
                "day_high":    round(day_high,   3),
                "day_low":     round(day_low,    3),
                "day_chg":     day_chg,
                "day_chg_pct": day_chg_pct,
                "day_pnl":     day_pnl,
                "mkt_value":   mkt_value,
                "pnl":         pnl,
                "pnl_pct":     pnl_pct,
                "total_div":   total_div,
                "annual_div":  annual_div,
                "div_yield":   div_yield,
                "tranches":    tranche_data,
            })

        except Exception as exc:
            logger.warning("Failed to enrich %s: %s — cost fallback", ticker_yf, exc)
            enriched.append({
                **h,
                "last_price":  h["avg_cost"], "prev_close":  h["avg_cost"],
                "day_high":    h["avg_cost"], "day_low":     h["avg_cost"],
                "day_chg":     0, "day_chg_pct": 0, "day_pnl": 0,
                "mkt_value":   round(h["total_shares"] * h["avg_cost"], 2),
                "pnl": 0, "pnl_pct": 0,
                "total_div": 0, "annual_div": 0, "div_yield": 0,
                "tranches": [],
            })

    result = {
        "holdings":   enriched,
        "histories":  histories,
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
    }
    set_cache(cache_key, result, ttl=CACHE_TTL_SECONDS)
    logger.info("Done — %d enriched, %d with history, cached %ds", len(enriched), len(histories), CACHE_TTL_SECONDS)
    return result
```

### services/market/status.py
```python
"""
Market status detection service.

Determines if markets are open or closed based on configurable hours.
"""

import logging
from datetime import datetime, time
from typing import Optional

from config.settings import MARKET_OPEN_TIME, MARKET_CLOSE_TIME, MARKET_TIMEZONE

logger = logging.getLogger(__name__)


def is_market_open(
    current_time: Optional[datetime] = None,
    open_time: str = MARKET_OPEN_TIME,
    close_time: str = MARKET_CLOSE_TIME,
    timezone: str = MARKET_TIMEZONE,
) -> bool:
    """
    Check if the market is currently open based on configurable hours.
    
    Args:
        current_time: Time to check (defaults to now)
        open_time: Market open time in HH:MM format
        close_time: Market close time in HH:MM format
        timezone: Timezone for market hours
    
    Returns:
        True if market is open, False otherwise
    """
    if current_time is None:
        current_time = datetime.now()
    
    # Parse market hours
    try:
        open_hour, open_minute = map(int, open_time.split(':'))
        close_hour, close_minute = map(int, close_time.split(':'))
    except ValueError as e:
        logger.error(f"Invalid market time format: open={open_time}, close={close_time}: {e}")
        return False
    
    # Create time objects for comparison
    market_open = time(open_hour, open_minute)
    market_close = time(close_hour, close_minute)
    
    # Get current time in market timezone
    try:
        # For simplicity, assuming local timezone matches market timezone
        # In production, you'd want proper timezone conversion
        current_market_time = current_time.time()
    except Exception as e:
        logger.error(f"Error getting current market time: {e}")
        return False
    
    # Check if current time is within market hours
    # Note: This is a simplified check that doesn't account for weekends/holidays
    is_open = market_open <= current_market_time <= market_close
    
    logger.debug(
        f"Market status check: current={current_market_time}, "
        f"open={market_open}, close={market_close}, is_open={is_open}"
    )
    
    return is_open


def get_market_status_message(
    current_time: Optional[datetime] = None,
    open_time: str = MARKET_OPEN_TIME,
    close_time: str = MARKET_CLOSE_TIME,
) -> str:
    """
    Get a human-readable market status message.
    
    Args:
        current_time: Time to check (defaults to now)
        open_time: Market open time in HH:MM format
        close_time: Market close time in HH:MM format
    
    Returns:
        Status message string
    """
    if current_time is None:
        current_time = datetime.now()
    
    if is_market_open(current_time, open_time, close_time):
        return f"Market Open ({open_time} - {close_time})"
    else:
        return f"Market Closed ({open_time} - {close_time})"
```

### pages/portfolio.py
```python
"""
pages/portfolio.py
==================
Dash Pages wrapper for the existing portfolio dashboard.
Route: /

Layout is delegated entirely to components/layout.py — nothing new here.
Stores, Interval, and all callbacks are registered in app.py.
"""

import dash
from components.layout import create_layout

dash.register_page(__name__, path="/", title="Portfolio — Live P&L")

# Dash Pages calls `layout` (or `layout()`) when the page is rendered.
# We call create_layout() without initial_history because txn-store is
# already seeded from app.layout.
layout = create_layout()
```

### pages/etf_detail.py
```python
"""
pages/etf_detail.py
====================
ETF detail drill-down page.
Route: /etf/<ticker>   e.g. /etf/VHY

Bug fixes in this version
--------------------------
1. LIGHT MODE  — All background/surface/border/text colours now use CSS
                 variables (var(--bg), var(--surface), etc.) instead of
                 hardcoded dark hex values, so the theme toggle works.

2. PERIOD FILTER — Selected period is stored in `dcc.Store` ("etf-period-store")
                   and written by a separate clientside callback.  The chart
                   callback reads from that store, not from button n_clicks
                   (which all start at 0 and can't be disambiguated on first
                   render or after a page reload).

3. DIVIDENDS    — `hist.get("Dividends")` fails on a DataFrame (no .get()).
                 Fixed to `hist["Dividends"] if "Dividends" in hist.columns`.
                 Also uses the tranche data already in portfolio-store instead
                 of re-fetching, so the cards always have data.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from dash import ALL, ClientsideFunction, Input, Output, State, dcc, html, register_page

from config.constants import (
    BG, SURFACE, BORDER, GREEN, RED, T_PRI, T_SEC, COLORS, PLOTLY_BASE, NAMES
)
from services.market.status import market_badge

# ── Register page ─────────────────────────────────────────────────────────────
register_page(__name__, path_template="/etf/<ticker>", title="ETF Detail")

# ── Period filter options ─────────────────────────────────────────────────────
PERIOD_OPTIONS = [
    {"label": "Since purchase", "value": "purchase"},
    {"label": "1M",  "value": "1mo"},
    {"label": "3M",  "value": "3mo"},
    {"label": "6M",  "value": "6mo"},
    {"label": "1Y",  "value": "1y"},
    {"label": "MAX", "value": "max"},
]
DEFAULT_PERIOD = "3mo"

# ── CSS-variable style tokens (theme-aware) ───────────────────────────────────
# Use CSS vars everywhere so dark/light toggle works without Python re-render.
_SECTION = {
    "padding":      "20px 24px",
    "borderBottom": "0.5px solid var(--border)",
}
_CARD = {
    "background":   "var(--surface)",
    "borderRadius": "10px",
    "padding":      "16px 20px",
    "flex":         "1",
    "minWidth":     "140px",
}
_TH = {
    "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "500",
    "padding": "7px 12px", "borderBottom": "1px solid var(--border)",
    "backgroundColor": "var(--surface)", "textAlign": "left",
    "whiteSpace": "nowrap",
}
_TD = {
    "fontSize": "13px", "padding": "8px 12px",
    "borderBottom": "0.5px solid var(--border)", "whiteSpace": "nowrap",
    "color": "var(--t-pri)",
}


# ── Small stat card ────────────────────────────────────────────────────────────
def _card(label: str, value: str, sub: str | None = None,
          color: str = "var(--t-pri)", sub_color: str = "var(--t-sec)") -> html.Div:
    children: list = [
        html.P(label, style={"fontSize": "11px", "color": "var(--t-sec)",
                              "margin": "0 0 4px"}),
        html.P(value, style={"fontSize": "20px", "fontWeight": "500",
                              "margin": "0", "color": color}),
    ]
    if sub:
        children.append(
            html.P(sub, style={"fontSize": "11px", "color": sub_color,
                                "margin": "3px 0 0"})
        )
    return html.Div(children, style=_CARD)


# ── Layout factory ────────────────────────────────────────────────────────────
def layout(ticker: str = "") -> html.Div:
    ticker = ticker.upper()
    name   = NAMES.get(ticker, ticker)

    return html.Div(
        [
            # Hidden stores
            dcc.Store(id="etf-ticker-store", data=ticker),
            dcc.Store(id="etf-period-store", data=DEFAULT_PERIOD),

            # ── A. Header ─────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.A(
                            "← Portfolio",
                            href="/",
                            style={
                                "fontSize": "12px",
                                "color": "var(--t-sec)",
                                "textDecoration": "none",
                                "display": "inline-block",
                                "marginBottom": "8px",
                                "letterSpacing": "0.02em",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    ticker,
                                    style={
                                        "fontSize":      "22px",
                                        "fontWeight":    "600",
                                        "background":    "var(--surface)",
                                        "border":        "1px solid var(--border)",
                                        "borderRadius":  "6px",
                                        "padding":       "2px 10px",
                                        "marginRight":   "12px",
                                        "letterSpacing": "0.04em",
                                        "color":         "var(--t-pri)",
                                    },
                                ),
                                html.Span(
                                    name,
                                    style={
                                        "fontSize":   "18px",
                                        "fontWeight": "400",
                                        "color":      "var(--t-sec)",
                                    },
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center",
                                   "flexWrap": "wrap", "gap": "4px"},
                        ),
                    ]),
                    html.Div(id="etf-market-status",
                             style={"alignSelf": "flex-start"}),
                ],
                style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "padding": "18px 24px 14px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── B. Price chart ────────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Price chart",
                                      style={"fontSize": "13px", "fontWeight": "500",
                                             "color": "var(--t-pri)"}),
                            # Period filter buttons
                            html.Div(
                                id="etf-period-btns",
                                children=_period_buttons(DEFAULT_PERIOD),
                                style={"display": "flex", "gap": "6px",
                                       "flexWrap": "wrap"},
                            ),
                        ],
                        style={
                            "display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "10px",
                            "flexWrap": "wrap", "gap": "10px",
                        },
                    ),
                    dcc.Loading(
                        dcc.Graph(id="etf-price-chart",
                                  config={"displayModeBar": False}),
                        type="circle",
                        color=COLORS[0],
                    ),
                ],
                style=_SECTION,
            ),

            # ── C. Position summary ───────────────────────────────────────────
            html.Div(
                [
                    html.Span("Position summary",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-position-cards",
                             style={"display": "flex", "gap": "10px",
                                    "flexWrap": "wrap"}),
                ],
                style=_SECTION,
            ),

            # ── D. Transaction table ──────────────────────────────────────────
            html.Div(
                [
                    html.Span("Transactions",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-txn-table", style={"overflowX": "auto"}),
                ],
                style=_SECTION,
            ),

            # ── E. Dividend section ───────────────────────────────────────────
            html.Div(
                [
                    html.Span("Dividends",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-dividend-cards",
                             style={"display": "flex", "gap": "10px",
                                    "flexWrap": "wrap", "marginBottom": "16px"}),
                    dcc.Loading(
                        dcc.Graph(id="etf-dividend-chart",
                                  config={"displayModeBar": False},
                                  style={"height": "260px"}),
                        type="circle",
                        color=COLORS[1],
                    ),
                ],
                style={**_SECTION, "borderBottom": "none"},
            ),
        ],
        # Use CSS vars for the outer wrapper too
        style={
            "backgroundColor": "var(--bg)",
            "color":           "var(--t-pri)",
            "minHeight":       "100vh",
        },
    )


# ── Period button renderer (also called from callback to update active state) ─
def _period_buttons(active: str) -> list:
    buttons = []
    for opt in PERIOD_OPTIONS:
        is_active = opt["value"] == active
        buttons.append(
            html.Button(
                opt["label"],
                id={"type": "etf-period-btn", "index": opt["value"]},
                n_clicks=0,
                style={
                    "fontSize":       "12px",
                    "padding":        "3px 12px",
                    "borderRadius":   "20px",
                    "cursor":         "pointer",
                    "fontWeight":     "500",
                    # Active button gets a solid accent border; inactive is muted
                    "background":     COLORS[0] if is_active else "var(--surface)",
                    "border":         f"1px solid {COLORS[0]}" if is_active
                                      else "1px solid var(--border)",
                    "color":          "#ffffff" if is_active else "var(--t-pri)",
                },
            )
        )
    return buttons


# ── Plotly layout base using CSS-var-aware colours ────────────────────────────
# Charts use the dark constants from config for paper/plot bg (Plotly doesn't
# read CSS vars). We keep the dark values here — charts look fine in both
# themes since they're canvas-rendered. Only the surrounding HTML needs vars.
_CHART_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)


# ── Callbacks ─────────────────────────────────────────────────────────────────
def register_callbacks(app) -> None:

    # ── Market badge ──────────────────────────────────────────────────────────
    @app.callback(
        Output("etf-market-status", "children"),
        Input("live-interval",      "n_intervals"),
    )
    def etf_market_badge(_):
        return market_badge()

    # ── Period store + button highlight ──────────────────────────────────────
    # One callback: clicking any period button writes to the store AND
    # re-renders the buttons so the active one is highlighted.
    @app.callback(
        Output("etf-period-store", "data"),
        Output("etf-period-btns",  "children"),
        Input({"type": "etf-period-btn", "index": ALL}, "n_clicks"),
        State({"type": "etf-period-btn", "index": ALL}, "id"),
        State("etf-period-store", "data"),
        prevent_initial_call=True,
    )
    def update_period(n_clicks_list, btn_ids, current_period):
        # Find which button was actually clicked (n_clicks just incremented)
        from dash import ctx
        if not ctx.triggered_id:
            return current_period, _period_buttons(current_period)
        clicked = ctx.triggered_id["index"]
        return clicked, _period_buttons(clicked)

    # ── Price chart ───────────────────────────────────────────────────────────
    @app.callback(
        Output("etf-price-chart", "figure"),
        Input("etf-ticker-store", "data"),
        Input("etf-period-store", "data"),
        Input("portfolio-store",  "data"),
    )
    def etf_price_chart(ticker, selected_period, port_data):
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False, rangeslider_visible=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            hovermode="x unified",
            height=380,
            **_CHART_LAYOUT,
        )

        if not ticker:
            return fig

        # Resolve first-purchase date and holding details from store
        first_purchase = None
        holding        = None
        if port_data and "holdings" in port_data:
            holding = next(
                (h for h in port_data["holdings"] if h["ticker"] == ticker), None
            )
            if holding:
                first_purchase = holding.get("first_purchase")

        ticker_yf = ticker + ".AX"
        try:
            tk = yf.Ticker(ticker_yf)
            if selected_period == "purchase" and first_purchase:
                df = tk.history(start=first_purchase)
            else:
                df = tk.history(period=selected_period)
        except Exception as exc:
            fig.add_annotation(
                text=f"Could not load price data: {exc}",
                showarrow=False, font=dict(color=T_SEC, size=12),
            )
            return fig

        if df.empty:
            fig.add_annotation(
                text="No price history for this period",
                showarrow=False, font=dict(color=T_SEC, size=13),
            )
            return fig

        # Normalise timezone
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        dates = df.index.strftime("%Y-%m-%d").tolist()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=dates,
            open=df["Open"].round(3).tolist(),
            high=df["High"].round(3).tolist(),
            low=df["Low"].round(3).tolist(),
            close=df["Close"].round(3).tolist(),
            name=ticker,
            increasing_line_color=GREEN,
            decreasing_line_color=RED,
            increasing_fillcolor=GREEN,
            decreasing_fillcolor=RED,
            line=dict(width=1),
        ))

        # Dotted avg-cost reference line
        if holding and holding.get("avg_cost"):
            fig.add_hline(
                y=holding["avg_cost"],
                line_dash="dot",
                line_color="rgba(255,255,255,0.30)",
                annotation_text=f"Avg cost  ${holding['avg_cost']:,.4f}",
                annotation_font_size=10,
                annotation_font_color=T_SEC,
                annotation_position="top left",
            )

        return fig

    # ── Position summary cards ────────────────────────────────────────────────
    @app.callback(
        Output("etf-position-cards", "children"),
        Input("etf-ticker-store",    "data"),
        Input("portfolio-store",     "data"),
    )
    def etf_position_cards(ticker, port_data):
        if not ticker or not port_data or "holdings" not in port_data:
            return html.P("Loading…",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return html.P(f"No active position for {ticker}.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        pnl     = h["pnl"];   psgn = "+" if pnl     >= 0 else ""; pc = GREEN if pnl     >= 0 else RED
        day_pnl = h["day_pnl"]; dsgn = "+" if day_pnl >= 0 else ""; dc = GREEN if day_pnl >= 0 else RED

        return [
            _card("Total invested",  f"${h['total_cost']:,.2f}"),
            _card("Current value",   f"${h['mkt_value']:,.2f}",
                  f"{h['total_shares']} shares @ ${h['last_price']:,.3f}"),
            _card("Unrealised P&L",
                  f"{psgn}${pnl:,.2f}",
                  f"{psgn}{h['pnl_pct']:.2f}%  all time", pc, pc),
            _card("Today's P&L",
                  f"{dsgn}${day_pnl:,.2f}",
                  f"{dsgn}{h['day_chg_pct']:.2f}%  today", dc, dc),
            _card("Avg cost",    f"${h['avg_cost']:,.4f}"),
            _card("Last price",  f"${h['last_price']:,.3f}",
                  f"H ${h['day_high']:,.3f}  /  L ${h['day_low']:,.3f}"),
        ]

    # ── Transaction table ─────────────────────────────────────────────────────
    @app.callback(
        Output("etf-txn-table",   "children"),
        Input("etf-ticker-store", "data"),
        Input("txn-store",        "data"),
    )
    def etf_txn_table(ticker, history):
        if not ticker or not history:
            return html.P("No transactions.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        rows_data = [t for t in history if t.get("ticker", "").upper() == ticker]
        if not rows_data:
            return html.P(f"No transactions found for {ticker}.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        rows          = []
        running_shares = 0.0
        running_cost   = 0.0

        for t in sorted(rows_data, key=lambda r: r["date"]):
            shares = float(t["shares"])
            price  = float(t["price"])
            total  = shares * price
            is_buy = t["type"] == "buy"
            tc     = GREEN if is_buy else RED

            if is_buy:
                running_shares += shares
                running_cost   += total
            else:
                if running_shares > 0:
                    running_cost -= shares * (running_cost / running_shares)
                running_shares -= shares

            rows.append(html.Tr([
                html.Td(t["date"],         style=_TD),
                html.Td(t["type"].upper(), style={**_TD, "color": tc,
                                                  "fontWeight": "600"}),
                html.Td(f"{shares:g}",     style=_TD),
                html.Td(f"${price:,.4f}",  style=_TD),
                html.Td(f"${total:,.2f}",  style=_TD),
                html.Td(f"{max(running_shares, 0):g}",
                        style={**_TD, "color": "var(--t-sec)"}),
                html.Td(f"${max(running_cost, 0):,.2f}",
                        style={**_TD, "color": "var(--t-sec)"}),
            ]))

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(c, style=_TH)
                        for c in ["Date", "Type", "Shares", "Price",
                                  "Total value", "Running shares",
                                  "Running cost basis"]
                    ])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse"},
            ),
            style={
                "borderRadius": "8px",
                "border":       "0.5px solid var(--border)",
                "overflowX":    "auto",
            },
        )

    # ── Dividend cards + per-year bar chart ───────────────────────────────────
    @app.callback(
        Output("etf-dividend-cards", "children"),
        Output("etf-dividend-chart", "figure"),
        Input("etf-ticker-store",    "data"),
        Input("portfolio-store",     "data"),
    )
    def etf_dividends(ticker, port_data):
        empty_fig = go.Figure()
        empty_fig.update_layout(
            **_CHART_LAYOUT, height=240,
            annotations=[dict(
                text="No dividend history available",
                showarrow=False, font=dict(color=T_SEC, size=13),
            )],
        )

        if not ticker or not port_data or "holdings" not in port_data:
            return [], empty_fig

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return [], empty_fig

        annual_div = h.get("annual_div", 0)
        div_yield  = h.get("div_yield",  0)
        total_div  = h.get("total_div",  0)

        cards = [
            _card("Annual income",
                  f"${annual_div:,.2f}",
                  "estimated · last 12 months",
                  GREEN if annual_div > 0 else "var(--t-pri)", "var(--t-sec)"),
            _card("Dividend yield",
                  f"{div_yield:.2f}%",
                  "annual income ÷ current value",
                  GREEN if div_yield > 0 else "var(--t-pri)", "var(--t-sec)"),
            _card("Total received",
                  f"${total_div:,.2f}",
                  "all time since first purchase"),
        ]

        # Per-year bar chart — fetch dividend history from yfinance
        try:
            tk   = yf.Ticker(ticker + ".AX")
            hist = tk.history(period="max")

            # FIX: DataFrame has no .get() — use column existence check
            if hist.empty or "Dividends" not in hist.columns:
                return cards, empty_fig

            div_s = hist["Dividends"]
            div_s = div_s[div_s > 0]

            if div_s.empty:
                return cards, empty_fig

            # Normalise timezone
            if div_s.index.tz is not None:
                div_s.index = div_s.index.tz_convert(None)

            # Scale per-share dividend to our share count
            div_s   = div_s * float(h.get("total_shares", 1))
            by_year = div_s.groupby(div_s.index.year).sum().round(2)
            years   = [str(y) for y in by_year.index]
            amounts = by_year.tolist()

            fig = go.Figure()
            fig.update_layout(
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor=BORDER, tickprefix="$"),
                height=240,
                **_CHART_LAYOUT,
            )
            fig.add_trace(go.Bar(
                x=years,
                y=amounts,
                marker_color=COLORS[1],
                text=[f"${v:,.2f}" for v in amounts],
                textposition="outside",
                textfont=dict(size=11, color=T_PRI),
                name="Annual dividends",
            ))
            return cards, fig

        except Exception:
            return cards, empty_fig
```

### callbacks/core_callbacks.py
```python
"""
callbacks/core_callbacks.py
============================
Main data refresh, stat cards, live positions table.

Colour tokens use CSS variables (var(--surface) etc.) so the table
renders correctly in both dark and light themes.
"""

from dash import Input, Output, html

from config.constants import GREEN, RED, T_PRI, T_SEC
from config.settings import REFRESH_INTERVAL
from data.portfolio_builder import build_holdings
from services.market.fetcher import fetch_live
from services.market.status import market_badge
from components.ui_helpers import stat_card


def register_callbacks(app) -> None:

    # ── Main data refresh ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-store", "data"),
        Output("last-updated",    "children"),
        Output("market-status",   "children"),
        Input("live-interval",    "n_intervals"),
        Input("refresh-btn",      "n_clicks"),
        Input("period-picker",    "value"),
        Input("txn-store",        "data"),
    )
    def refresh(_, __, period, history):
        holdings = build_holdings(history or [])
        if not holdings:
            return {}, "No holdings — check your CSV.", market_badge()
        data = fetch_live(holdings, period)
        return data, f"Updated {data.get('fetched_at', '')}", market_badge()

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards", "children"),
        Input("portfolio-store", "data"),
    )
    def update_stats(data):
        if not data or "holdings" not in data:
            return []

        h          = data["holdings"]
        total_val  = sum(x["mkt_value"]  for x in h)
        total_cost = sum(x["total_cost"] for x in h)
        total_pnl  = total_val - total_cost
        pnl_pct    = (total_pnl / total_cost * 100) if total_cost else 0
        total_day  = sum(x["day_pnl"]    for x in h)
        annual_div = sum(x["annual_div"] for x in h)
        port_yield = (annual_div / total_val * 100) if total_val else 0

        ps = "+" if total_pnl >= 0 else ""
        ds = "+" if total_day >= 0 else ""
        pc = GREEN if total_pnl >= 0 else RED
        dc = GREEN if total_day >= 0 else RED

        return [
            stat_card("Total value",      f"${total_val:,.2f}"),
            stat_card("Cost basis",       f"${total_cost:,.2f}"),
            stat_card("Unrealised P&L",   f"{ps}${total_pnl:,.2f}",
                      f"{ps}{pnl_pct:.2f}% all time", pc, pc),
            stat_card("Today's P&L",      f"{ds}${total_day:,.2f}",
                      "across all positions", dc, dc),
            stat_card("Annual dividends", f"${annual_div:,.2f}",
                      f"{port_yield:.2f}% yield",
                      GREEN if port_yield > 0 else "var(--t-pri)",
                      "var(--t-sec)"),
            stat_card("Holdings", str(len(h))),
        ]

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table", "children"),
        Input("portfolio-store", "data"),
    )
    def update_live_table(data):
        if not data or "holdings" not in data:
            return html.P("Loading...",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        h  = data["holdings"]
        th = {
            "fontSize":        "11px",
            "color":           "var(--t-sec)",
            "fontWeight":      "500",
            "padding":         "7px 12px",
            "textAlign":       "left",
            "borderBottom":    "1px solid var(--border)",
            "backgroundColor": "var(--surface)",
            "whiteSpace":      "nowrap",
        }
        td = {
            "fontSize":     "13px",
            "padding":      "8px 12px",
            "borderBottom": "0.5px solid var(--border)",
            "whiteSpace":   "nowrap",
            "color":        "var(--t-pri)",
        }

        def pnl_td(val, pct):
            c = GREEN if val >= 0 else RED
            s = "+" if val >= 0 else ""
            return html.Td(
                [
                    html.Div(f"{s}${val:,.2f}",
                             style={"color": c, "fontWeight": "500",
                                    "fontSize": "13px"}),
                    html.Div(f"{s}{pct:.2f}%",
                             style={"color": c, "fontSize": "11px"}),
                ],
                style=td,
            )

        rows = []
        for x in sorted(h, key=lambda v: v["mkt_value"], reverse=True):
            dc = GREEN if x["day_chg"] >= 0 else RED
            ds = "+" if x["day_chg"] >= 0 else ""
            rows.append(html.Tr([
                # Ticker links to ETF detail page
                html.Td(
                    html.A(x["ticker"], href=f"/etf/{x['ticker']}",
                           className="ticker-link"),
                    style=td,
                ),
                html.Td(x.get("name", ""),
                        style={**td, "color": "var(--t-sec)",
                               "fontSize": "12px"}),
                html.Td(str(x["total_shares"]), style=td),
                html.Td(f"${x['avg_cost']:,.4f}",  style=td),
                html.Td(f"${x['last_price']:,.3f}", style=td),
                html.Td(
                    [
                        html.Div(f"{ds}${x['day_chg']:,.3f}",
                                 style={"color": dc, "fontWeight": "500",
                                        "fontSize": "13px"}),
                        html.Div(f"{ds}{x['day_chg_pct']:.2f}%",
                                 style={"color": dc, "fontSize": "11px"}),
                    ],
                    style=td,
                ),
                html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                        style={**td, "fontSize": "12px",
                               "color": "var(--t-sec)"}),
                html.Td(f"${x['mkt_value']:,.2f}", style=td),
                html.Td(f"${x['total_cost']:,.2f}", style=td),
                pnl_td(x["pnl"],     x["pnl_pct"]),
                pnl_td(x["day_pnl"], x["day_chg_pct"]),
                html.Td(f"{x['div_yield']:.2f}%", style=td),
            ]))

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(c, style=th)
                        for c in [
                            "Ticker", "Name", "Shares", "Avg cost",
                            "Last price", "Day change", "High / Low",
                            "Market value", "Cost basis",
                            "Unrealised P&L", "Today's P&L", "Div yield",
                        ]
                    ])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse",
                       "overflowX": "auto", "display": "block"},
            ),
            style={
                "overflowX":    "auto",
                "borderRadius": "8px",
                "border":       "0.5px solid var(--border)",
            },
        )
```

### callbacks/transaction_callbacks.py
```python
import pandas as pd
from datetime import datetime
from dash import Input, Output, State

from config.constants import GREEN, RED
from data.csv_handler import save_csv
from components.ui_helpers import txn_table


def register_callbacks(app) -> None:

    @app.callback(
        Output("txn-store",  "data"),
        Output("txn-msg",    "children"),
        Output("txn-msg",    "style"),
        Input("txn-submit",  "n_clicks"),
        State("txn-type",    "value"),
        State("txn-ticker",  "value"),
        State("txn-shares",  "value"),
        State("txn-price",   "value"),
        State("txn-date",    "value"),
        State("txn-store",   "data"),
        prevent_initial_call=True,
    )
    def add_transaction(_, txn_type, ticker, shares, price, date, history):
        base = {"fontSize": "12px", "marginTop": "8px", "minHeight": "18px"}

        # ── Basic validation ──────────────────────────────────────────────────
        if not ticker or shares is None or price is None:
            return history, "Please fill in ticker, shares and price.", {**base, "color": RED}

        ticker = ticker.strip().upper()
        try:
            shares = float(shares)
            price  = float(price)
        except (TypeError, ValueError):
            return history, "Shares and price must be numbers.", {**base, "color": RED}

        if shares <= 0 or price <= 0:
            return history, "Shares and price must be positive.", {**base, "color": RED}

        try:
            datetime.strptime(date.strip(), "%Y-%m-%d")
        except (ValueError, AttributeError):
            return history, "Date must be YYYY-MM-DD (e.g. 2026-03-30).", {**base, "color": RED}

        # ── Sell validation ───────────────────────────────────────────────────
        if txn_type == "sell":
            df = pd.DataFrame(history)
            if df.empty or ticker not in df["ticker"].values:
                return history, f"No holdings found for {ticker}.", {**base, "color": RED}
            grp  = df[df["ticker"] == ticker]
            held = (
                grp[grp["type"] == "buy"]["shares"].sum()
                - grp[grp["type"] == "sell"]["shares"].sum()
                if "sell" in grp["type"].values
                else grp[grp["type"] == "buy"]["shares"].sum()
            )
            if shares > held:
                return history, f"Cannot sell {shares} — only holding {held}.", {**base, "color": RED}

        # ── Commit ────────────────────────────────────────────────────────────
        new_txn = {
            "type":   txn_type,
            "ticker": ticker,
            "shares": shares,
            "price":  price,
            "date":   date.strip(),
        }
        updated = history + [new_txn]

        try:
            save_csv(updated)
            msg = f"{txn_type.capitalize()} {shares} {ticker} @ ${price:.4f} saved to CSV."
        except Exception as e:
            msg = f"Added to dashboard but CSV save failed: {e}"

        color = GREEN if txn_type == "buy" else RED
        return updated, msg, {**base, "color": color}

    # ── Transaction log display ───────────────────────────────────────────────

    @app.callback(
        Output("txn-log", "children"),
        Input("txn-store", "data"),
    )
    def update_txn_log(history):
        return txn_table(history)
```

### callbacks/chart_callbacks.py
```python
import logging
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html

from config.constants import GREEN, RED, COLORS, get_theme

logger = logging.getLogger(__name__)


def register_callbacks(app) -> None:

    # ── Ticker toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("ticker-toggle-btns", "children"),
        Input("portfolio-store",     "data"),
        Input("theme-store",         "data"),
    )
    def build_toggle_btns(data, theme):
        t_ = get_theme(theme or "dark")
        T_PRI = t_["T_PRI"]
        if not data or "holdings" not in data:
            return []
        tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
        return [
            html.Button(
                t,
                id={"type": "ticker-btn", "index": t},
                n_clicks=0,
                style={
                    "fontSize":     "12px",
                    "padding":      "4px 12px",
                    "borderRadius": "20px",
                    "cursor":       "pointer",
                    "fontWeight":   "500",
                    "background":   "transparent",
                    "border":       f"1.5px solid {T_PRI if t == 'Portfolio' else COLORS[(i - 1) % len(COLORS)]}",
                    "color":        T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)],
                },
            )
            for i, t in enumerate(tickers)
        ]

    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("pnl-mode",           "value"),
        Input("theme-store",        "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State({"type": "ticker-btn", "index": ALL}, "id"),
    )
    def pnl_history_chart(data, mode, theme, n_clicks_list, btn_ids):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(
                gridcolor=BORDER,
                ticksuffix="%" if mode == "pct" else "",
                tickprefix="" if mode == "pct" else "$",
                zeroline=True, zerolinecolor=BORDER, zerolinewidth=1,
            ),
            hovermode="x unified",
            height=380,
            **PLOTLY_BASE,
        )

        if not data or "holdings" not in data:
            return fig

        selected = "Portfolio"
        if n_clicks_list and any(n and n > 0 for n in n_clicks_list):
            last_idx = max(range(len(n_clicks_list)), key=lambda i: n_clicks_list[i] or 0)
            selected = btn_ids[last_idx]["index"]

        holdings  = data["holdings"]
        color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}

        if selected == "Portfolio":
            series = {}
            for h in holdings:
                for tr in h.get("tranches", []):
                    idx = pd.to_datetime(tr["dates"])
                    key = f"{h['ticker']}_{tr['buy_date']}"
                    series[key] = {
                        "pnl":  pd.Series(tr["pnl"], index=idx),
                        "cost": pd.Series([tr["shares"] * tr["buy_price"]] * len(idx), index=idx),
                    }
            if series:
                cpnl  = pd.concat([v["pnl"]  for v in series.values()], axis=1).ffill().sum(axis=1).sort_index()
                ccost = pd.concat([v["cost"] for v in series.values()], axis=1).ffill().sum(axis=1).sort_index()
                y  = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)
                lv = y.iloc[-1] if len(y) else 0
                lc = GREEN if lv >= 0 else RED
                fc = "rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)"
                fig.add_trace(go.Scatter(
                    x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=y.tolist(),
                    name="Portfolio", mode="lines", fill="tozeroy", fillcolor=fc,
                    line=dict(color=lc, width=2.5),
                    hovertemplate=("%{y:.2f}%<extra>Portfolio</extra>" if mode == "pct"
                                   else "$%{y:,.2f}<extra>Portfolio</extra>"),
                ))
        else:
            hm = next((h for h in holdings if h["ticker"] == selected), None)
            if hm:
                tranches = hm.get("tranches", [])
                bc = color_map.get(selected, COLORS[0])
                if len(tranches) == 1:
                    tr = tranches[0]
                    fig.add_trace(go.Scatter(
                        x=tr["dates"], y=tr["pct"] if mode == "pct" else tr["pnl"],
                        name=selected, mode="lines", fill="tozeroy",
                        fillcolor="rgba(55,138,221,0.10)",
                        line=dict(color=bc, width=2.5),
                    ))
                else:
                    pnl_p, cost_p = [], []
                    for tr in tranches:
                        idx   = pd.to_datetime(tr["dates"])
                        pnl_s = pd.Series(tr["pnl"], index=idx)
                        cst_s = pd.Series([tr["shares"] * tr["buy_price"]] * len(idx), index=idx)
                        pnl_p.append(cst_s)
                        cost_p.append(cst_s)
                        fig.add_trace(go.Scatter(
                            x=tr["dates"], y=tr["pct"] if mode == "pct" else tr["pnl"],
                            name=f"  {tr['buy_date']} ({int(tr['shares'])} shares)",
                            mode="lines", line=dict(color=bc, width=1, dash="dot"), opacity=0.45,
                        ))
                    cpnl  = pd.concat(pnl_p,  axis=1).ffill().sum(axis=1).sort_index()
                    ccost = pd.concat(cost_p, axis=1).ffill().sum(axis=1).sort_index()
                    yc    = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)
                    fig.add_trace(go.Scatter(
                        x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=yc.tolist(),
                        name=f"{selected} (combined)", mode="lines",
                        fill="tozeroy", fillcolor="rgba(55,138,221,0.10)",
                        line=dict(color=bc, width=2.5),
                    ))

        fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
        return fig

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BORDER), **PLOTLY_BASE)
        if not data or "histories" not in data:
            return fig
        for i, (t, recs) in enumerate(data["histories"].items()):
            df = pd.DataFrame(recs)
            if df.empty or not df["Close"].iloc[0]:
                continue
            fig.add_trace(go.Scatter(
                x=df["Date"], y=(df["Close"] / df["Close"].iloc[0] * 100).round(2),
                name=t, mode="lines",
                line=dict(color=COLORS[i % len(COLORS)], width=1.8),
            ))
        fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
        return fig

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BG = t_["BG"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "holdings" not in data:
            return fig
        h = data["holdings"]
        fig.add_trace(go.Pie(
            labels=[x["ticker"] for x in h],
            values=[x["mkt_value"] for x in h],
            hole=0.45,
            marker=dict(colors=COLORS[:len(h)], line=dict(color=BG, width=2)),
            textinfo="label+percent",
            textfont=dict(size=12),
        ))
        return fig

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER,
                       ticksuffix="%" if mode == "pct" else "",
                       tickprefix="" if mode == "pct" else "$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        key = "pnl_pct" if mode == "pct" else "pnl"
        h   = sorted(data["holdings"], key=lambda x: x[key])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x[key] for x in h],
            marker_color=[GREEN if x[key] >= 0 else RED for x in h],
            text=[f"{'+' if x[key] >= 0 else ''}{'%' if mode == 'pct' else '$'}{abs(x[key]):,.2f}" for x in h],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = sorted(data["holdings"], key=lambda x: x["day_pnl"])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x["day_pnl"] for x in h],
            marker_color=[GREEN if x["day_pnl"] >= 0 else RED for x in h],
            text=[f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct'] >= 0 else ''}{x['day_chg_pct']:.2f}%" for x in h],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Annual dividend income ────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart", "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, theme):
        t_ = get_theme(theme or "dark")
        T_SEC = t_["T_SEC"]
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = [x for x in data["holdings"] if x["annual_div"] > 0]
        if not h:
            fig.add_annotation(text="No dividend data yet — holdings are recent",
                               showarrow=False, font=dict(color=T_SEC, size=13))
            return fig
        h_s = sorted(h, key=lambda x: x["annual_div"], reverse=True)
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h_s],
            y=[x["annual_div"] for x in h_s],
            marker_color=COLORS[1],
            text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
            textposition="outside", textfont=dict(size=11),
        ))
        return fig

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def corr_chart(data, theme):
        t_ = get_theme(theme or "dark")
        T_SEC = t_["T_SEC"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "histories" not in data or len(data["histories"]) < 2:
            fig.add_annotation(text="Need 2+ holdings with history",
                               showarrow=False, font=dict(color=T_SEC, size=13))
            return fig

        dfs = {}
        for t, r in data["histories"].items():
            s = pd.DataFrame(r).set_index("Date")["Close"].pct_change().dropna()
            if len(s) >= 10:
                dfs[t] = s

        if len(dfs) < 2:
            fig.add_annotation(text="Need 2+ holdings with at least 10 days of history",
                               showarrow=False, font=dict(color=T_SEC, size=13))
            return fig

        corr  = pd.DataFrame(dfs).corr(min_periods=10).round(2)
        ticks = list(corr.columns)
        fig.add_trace(go.Heatmap(
            z=corr.values.tolist(), x=ticks, y=ticks,
            colorscale=[[0, "#1D9E75"], [0.5, "#EF9F27"], [1, "#E24B4A"]],
            zmin=-1, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in corr.values.tolist()],
            texttemplate="%{text}", textfont=dict(size=11),
            showscale=True, colorbar=dict(thickness=12, len=0.8),
        ))
        fig.update_layout(
            xaxis=dict(showgrid=False, tickfont=dict(size=11)),
            yaxis=dict(showgrid=False, tickfont=dict(size=11), autorange="reversed"),
        )
        return fig
```

### callbacks/alert_callbacks.py
```python
from dash import Input, Output, html
from config.constants import RED
from services.alerts import check_alerts


def register_callbacks(app) -> None:

    @app.callback(
        Output("alerts-banner", "children"),
        Input("portfolio-store", "data"),
    )
    def show_alerts(data):
        if not data or "holdings" not in data:
            return ""

        alerts = check_alerts(data["holdings"])
        if not alerts:
            return ""

        return html.Div(
            [html.Div(a["message"]) for a in alerts],
            style={
                "background":    "#2a0f0f",
                "color":         RED,
                "padding":       "10px 24px",
                "borderRadius":  "0",
                "marginBottom":  "0",
                "fontSize":      "13px",
                "borderBottom":  f"0.5px solid {RED}",
            },
        )
```

### callbacks/ui_callbacks.py
```python
from dash import Input, Output, State


def register_callbacks(app) -> None:

    # ── Dark / light theme toggle ─────────────────────────────────────────────
    app.clientside_callback(
        """
        function(n, current) {
            // If this is initial call (n is null/undefined), use current theme
            // If button was clicked (n > 0), toggle the theme
            const shouldToggle = n > 0;
            const theme = shouldToggle ? (current === 'dark' ? 'light' : 'dark') : current;
            
            document.body.setAttribute('data-theme', theme);
            document.documentElement.style.backgroundColor = theme === 'dark' ? '#111110' : '#ffffff';
            return theme;
        }
        """,
        Output("theme-store",    "data"),
        Input("theme-toggle",    "n_clicks"),
        State("theme-store",     "data"),
    )

    # ── PDF / print button ────────────────────────────────────────────────────
    app.clientside_callback(
        "function(n) { if(n) window.print(); return ''; }",
        Output("pdf-btn", "children"),   # dummy output — just needs somewhere to write
        Input("pdf-btn",  "n_clicks"),
        prevent_initial_call=True,
    )
```

### components/layout.py
```python
"""
components/layout.py
====================
Portfolio page layout.

All colours use CSS variables (var(--bg), var(--surface), var(--border),
var(--t-pri), var(--t-sec)) so the dark/light theme toggle works correctly.
The only remaining hardcoded hex values are GREEN (always green) and the
Plotly chart backgrounds (Plotly cannot read CSS vars at canvas render time).
"""

from datetime import datetime
from dash import dcc, html
from config.constants import GREEN
from config.settings import CSV_PATH
from components.ui_helpers import chart_title, section

# ── CSS injected into <head> ───────────────────────────────────────────────────
INDEX_STRING = '''
<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
/* ── Theme tokens ── */
body[data-theme="dark"] {
  --bg: #111110; --surface: #1c1c1a; --border: rgba(255,255,255,0.08);
  --t-pri: #f0ede8; --t-sec: #8a8880;
}
body[data-theme="light"] {
  --bg: #ffffff; --surface: #f8f8f6; --border: rgba(0,0,0,0.09);
  --t-pri: #1a1a1a; --t-sec: #6b6b67;
}

/* ── Global resets ── */
body {
  background-color: var(--bg) !important;
  color: var(--t-pri) !important;
}

/* ── Form elements ── */
input, select, button {
  background: var(--surface) !important;
  color: var(--t-pri) !important;
  border: 1px solid var(--border) !important;
}
input::placeholder { color: var(--t-sec) !important; }

/* ── Dash Dropdown (Select) ── */
.Select-control,
.Select { background: var(--surface) !important; color: var(--t-pri) !important; }
.Select input { background: transparent !important; color: var(--t-pri) !important; }
.Select-menu-outer, .Select .Select-menu-outer {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}
.Select-option, .Select .Select-option {
  background: var(--surface) !important;
  color: var(--t-pri) !important;
}
.Select-option:hover, .Select .Select-option:hover {
  background: var(--bg) !important;
}
.Select-value-label { color: var(--t-pri) !important; }
.Select-placeholder  { color: var(--t-sec) !important; }

/* ── ETF ticker links in live table ── */
a.ticker-link {
  color: var(--t-pri);
  text-decoration: none;
  font-weight: 500;
  border-bottom: 1px solid var(--border);
  transition: border-color 0.15s;
}
a.ticker-link:hover { border-color: var(--t-sec); }

/* ── Details/summary ── */
details summary { color: var(--t-sec); }

/* ── Print / PDF ── */
@media print {
  #controls-bar, #txn-panel, #toggle-area,
  button, .Select, [id$="-btn"] { display: none !important; }
  body { background: white !important; }
  .js-plotly-plot { break-inside: avoid; }
  @page { size: A4 landscape; margin: 1.5cm; }
}
</style>
</head>
<body data-theme="dark">{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>
'''


def create_layout(initial_history: list[dict] | None = None) -> html.Div:
    """
    Portfolio page inner content.
    Stores / Interval are in app.layout — do NOT add them here.
    """
    return html.Div(
        [
            # ── Header ────────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1(
                            "Portfolio — Live P&L",
                            style={"margin": "0", "fontSize": "20px",
                                   "fontWeight": "500", "color": "var(--t-pri)"},
                        ),
                        html.P(
                            "Auto-refreshes every 60 s · Yahoo Finance · ASX ETFs",
                            style={"margin": "3px 0 0", "fontSize": "12px",
                                   "color": "var(--t-sec)"},
                        ),
                        html.Button(
                            "☀ / ☾", id="theme-toggle", n_clicks=0,
                            style={"fontSize": "12px", "padding": "4px 10px"},
                        ),
                    ]),
                    html.Div(
                        [
                            html.Div(id="market-status"),
                            html.Span(id="last-updated",
                                      style={"fontSize": "12px",
                                             "color": "var(--t-sec)"}),
                        ],
                        style={"display": "flex", "flexDirection": "column",
                               "alignItems": "flex-end", "gap": "6px"},
                    ),
                ],
                style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "flex-start", "padding": "18px 24px 12px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Controls bar ─────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.P("Chart period",
                               style={"fontSize": "12px", "color": "var(--t-sec)",
                                      "margin": "0 0 4px"}),
                        dcc.Dropdown(
                            id="period-picker",
                            options=[
                                {"label": "Since purchase", "value": "max"},
                                {"label": "1 month",        "value": "1mo"},
                                {"label": "3 months",       "value": "3mo"},
                                {"label": "6 months",       "value": "6mo"},
                                {"label": "1 year",         "value": "1y"},
                                {"label": "2 years",        "value": "2y"},
                            ],
                            value="3mo", clearable=False,
                            style={"width": "155px", "fontSize": "13px"},
                        ),
                    ]),
                    html.Div([
                        html.P("P&L view",
                               style={"fontSize": "12px", "color": "var(--t-sec)",
                                      "margin": "0 0 4px"}),
                        dcc.Dropdown(
                            id="pnl-mode",
                            options=[
                                {"label": "Dollar ($)",     "value": "dollar"},
                                {"label": "Percentage (%)", "value": "pct"},
                            ],
                            value="dollar", clearable=False,
                            style={"width": "155px", "fontSize": "13px"},
                        ),
                    ]),
                    html.Button(
                        "Refresh now", id="refresh-btn", n_clicks=0,
                        style={"fontWeight": "500", "alignSelf": "flex-end"},
                    ),
                    html.Button(
                        "⬇ Download PDF", id="pdf-btn", n_clicks=0,
                        style={"fontWeight": "500", "alignSelf": "flex-end"},
                    ),
                ],
                style={
                    "display": "flex", "gap": "16px", "alignItems": "flex-end",
                    "padding": "14px 24px",
                    "borderBottom": "0.5px solid var(--border)",
                    "flexWrap": "wrap",
                },
            ),

            # ── Stat cards ────────────────────────────────────────────────────
            html.Div(
                id="stat-cards",
                style={
                    "display": "flex", "gap": "10px", "padding": "16px 24px",
                    "flexWrap": "wrap",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Transaction panel ─────────────────────────────────────────────
            html.Div(
                [
                    html.P("Add transaction",
                           style={"fontSize": "13px", "fontWeight": "500",
                                  "margin": "0 0 4px", "color": "var(--t-pri)"}),
                    html.P(
                        f"Saved to: {CSV_PATH}",
                        style={"fontSize": "11px", "color": "var(--t-sec)",
                               "margin": "0 0 12px", "fontFamily": "monospace"},
                    ),
                    html.Div(
                        [
                            html.Div([
                                html.P("Type",
                                       style={"fontSize": "11px",
                                              "color": "var(--t-sec)",
                                              "margin": "0 0 4px"}),
                                dcc.Dropdown(
                                    id="txn-type",
                                    options=[{"label": "Buy",  "value": "buy"},
                                             {"label": "Sell", "value": "sell"}],
                                    value="buy", clearable=False,
                                    style={"width": "100px", "fontSize": "13px"},
                                ),
                            ]),
                            html.Div([
                                html.P("Ticker",
                                       style={"fontSize": "11px",
                                              "color": "var(--t-sec)",
                                              "margin": "0 0 4px"}),
                                dcc.Input(
                                    id="txn-ticker", type="text",
                                    placeholder="e.g. VHY",
                                    style={"width": "90px", "fontSize": "13px",
                                           "padding": "6px 8px",
                                           "border": "0.5px solid var(--border)",
                                           "borderRadius": "6px"},
                                ),
                            ]),
                            html.Div([
                                html.P("Shares",
                                       style={"fontSize": "11px",
                                              "color": "var(--t-sec)",
                                              "margin": "0 0 4px"}),
                                dcc.Input(
                                    id="txn-shares", type="number",
                                    placeholder="0",
                                    style={"width": "90px", "fontSize": "13px",
                                           "padding": "6px 8px",
                                           "border": "0.5px solid var(--border)",
                                           "borderRadius": "6px"},
                                ),
                            ]),
                            html.Div([
                                html.P("Price ($)",
                                       style={"fontSize": "11px",
                                              "color": "var(--t-sec)",
                                              "margin": "0 0 4px"}),
                                dcc.Input(
                                    id="txn-price", type="number",
                                    placeholder="0.00",
                                    style={"width": "100px", "fontSize": "13px",
                                           "padding": "6px 8px",
                                           "border": "0.5px solid var(--border)",
                                           "borderRadius": "6px"},
                                ),
                            ]),
                            html.Div([
                                html.P("Date (YYYY-MM-DD)",
                                       style={"fontSize": "11px",
                                              "color": "var(--t-sec)",
                                              "margin": "0 0 4px"}),
                                dcc.Input(
                                    id="txn-date", type="text",
                                    value=datetime.now().strftime("%Y-%m-%d"),
                                    style={"width": "130px", "fontSize": "13px",
                                           "padding": "6px 8px",
                                           "border": "0.5px solid var(--border)",
                                           "borderRadius": "6px"},
                                ),
                            ]),
                            html.Div([
                                html.P("\u00a0",
                                       style={"fontSize": "11px",
                                              "margin": "0 0 4px"}),
                                html.Button(
                                    "Add transaction", id="txn-submit", n_clicks=0,
                                    style={"fontWeight": "500", "fontSize": "13px",
                                           "padding": "7px 16px"},
                                ),
                            ]),
                        ],
                        style={"display": "flex", "gap": "12px",
                               "flexWrap": "wrap", "alignItems": "flex-end"},
                    ),
                    html.P(
                        id="txn-msg",
                        style={"fontSize": "12px", "marginTop": "8px",
                               "minHeight": "18px", "color": GREEN},
                    ),
                    html.Details([
                        html.Summary(
                            "Transaction history",
                            style={"fontSize": "12px", "color": "var(--t-sec)",
                                   "cursor": "pointer", "marginTop": "8px"},
                        ),
                        html.Div(id="txn-log",
                                 style={"marginTop": "10px", "overflowX": "auto"}),
                    ]),
                ],
                style={
                    "padding":      "16px 24px",
                    "background":   "var(--surface)",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Live positions table ──────────────────────────────────────────
            section(chart_title("Live positions"), html.Div(id="live-table")),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                chart_title("P&L from purchase date", "pnl-history"),
                html.Div([
                    html.Div(
                        [
                            html.P("View:",
                                   style={"fontSize": "12px",
                                          "color": "var(--t-sec)",
                                          "margin": "0 8px 0 0",
                                          "alignSelf": "center"}),
                            html.Div(id="ticker-toggle-btns",
                                     style={"display": "flex", "gap": "6px",
                                            "flexWrap": "wrap"}),
                        ],
                        style={"display": "flex", "alignItems": "center",
                               "marginBottom": "12px", "flexWrap": "wrap"},
                    ),
                    dcc.Graph(id="pnl-history-chart",
                              config={"displayModeBar": False}),
                ]),
            ),

            # ── Charts grid ───────────────────────────────────────────────────
            html.Div(
                [
                    # Row 1
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Price history — normalised to 100",
                                             "price-chart"),
                                 dcc.Graph(id="price-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "2", "minWidth": "280px"},
                            ),
                            html.Div(
                                [chart_title("Portfolio allocation", "allocation"),
                                 dcc.Graph(id="allocation-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "220px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    # Row 2
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 dcc.Graph(id="pnl-bar-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 dcc.Graph(id="day-pnl-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    # Row 3
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 dcc.Graph(id="dividend-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Return correlation matrix",
                                             "correlation"),
                                 dcc.Graph(id="corr-chart",
                                           config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap"},
                    ),
                ],
                style={"padding": "16px 24px"},
            ),
        ],
    )
```

### components/ui_helpers.py
```python
"""
components/ui_helpers.py
=========================
Shared UI helpers.

All colours use CSS variables so the dark/light theme toggle works.
GREEN and RED remain hardcoded hex because they are semantic (profit/loss)
and should never invert with the theme.
"""

from dash import html
from config.constants import GREEN, RED, CHART_INFO


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = "var(--t-pri)",
    sub_color: str = "var(--t-sec)",
) -> html.Div:
    return html.Div(
        [
            html.P(label,
                   style={"fontSize": "12px", "color": "var(--t-sec)",
                           "margin": "0 0 4px"}),
            html.P(value,
                   style={"fontSize": "20px", "fontWeight": "500",
                           "margin": "0", "color": color}),
            html.P(sub,
                   style={"fontSize": "11px", "color": sub_color,
                           "margin": "3px 0 0"}) if sub else None,
        ],
        style={
            "background":   "var(--surface)",
            "borderRadius": "10px",
            "padding":      "14px 18px",
            "flex":         "1",
            "minWidth":     "130px",
        },
    )


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Chart section title with an optional hoverable (i) info badge."""
    tip = CHART_INFO.get(info_key, ("", ""))[1] if info_key else ""
    children = [
        html.Span(label,
                  style={"fontSize": "13px", "fontWeight": "500",
                          "color": "var(--t-pri)"})
    ]
    if tip:
        children.append(
            html.Span("i", title=tip, style={
                "display":        "inline-flex",
                "alignItems":     "center",
                "justifyContent": "center",
                "width":          "16px",
                "height":         "16px",
                "borderRadius":   "50%",
                "background":     "var(--surface)",
                "border":         "1px solid var(--border)",
                "fontSize":       "10px",
                "color":          "var(--t-sec)",
                "cursor":         "help",
                "marginLeft":     "6px",
                "fontWeight":     "500",
            })
        )
    return html.Div(
        children,
        style={"display": "inline-flex", "alignItems": "center",
               "marginBottom": "6px"},
    )


def section(title_node: html.Div, children) -> html.Div:
    return html.Div(
        [title_node, children],
        style={"padding": "16px 24px",
               "borderBottom": "0.5px solid var(--border)"},
    )


def txn_table(history: list[dict]) -> html.Element:
    """Render the transaction log as an HTML table."""
    if not history:
        return html.P("No transactions yet.",
                      style={"color": "var(--t-sec)", "fontSize": "13px"})

    th_s = {
        "fontSize":        "11px",
        "color":           "var(--t-sec)",
        "fontWeight":      "500",
        "padding":         "6px 10px",
        "borderBottom":    "1px solid var(--border)",
        "backgroundColor": "var(--surface)",
        "textAlign":       "left",
        "whiteSpace":      "nowrap",
    }
    td_s = {
        "fontSize":     "12px",
        "padding":      "6px 10px",
        "borderBottom": "0.5px solid var(--border)",
        "whiteSpace":   "nowrap",
        "color":        "var(--t-pri)",
    }

    rows = [
        html.Tr([
            html.Td(t["date"],   style=td_s),
            html.Td(t["ticker"], style={**td_s, "fontWeight": "500"}),
            html.Td(
                t["type"].upper(),
                style={**td_s,
                       "color": GREEN if t["type"] == "buy" else RED,
                       "fontWeight": "500"},
            ),
            html.Td(str(t["shares"]),                                    style=td_s),
            html.Td(f"${float(t['price']):,.4f}",                        style=td_s),
            html.Td(f"${float(t['shares']) * float(t['price']):,.2f}",   style=td_s),
        ])
        for t in reversed(history)
    ]

    return html.Table(
        [
            html.Thead(html.Tr([
                html.Th(c, style=th_s)
                for c in ["Date", "Ticker", "Type", "Shares", "Price", "Total"]
            ])),
            html.Tbody(rows),
        ],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
```

### data/csv_handler.py
```python
import logging
import os
import shutil
from pathlib import Path
import pandas as pd
from config.settings import CSV_PATH

logger = logging.getLogger(__name__)


def load_csv() -> list[dict]:
    """
    Load transactions from CSV.
    Returns list of dicts with keys: type, ticker, shares, price, date (YYYY-MM-DD).
    Raises FileNotFoundError / ValueError with clear messages if anything is wrong
    so the error prints to terminal rather than silently returning an empty list.

    Accepted date formats: YYYY-MM-DD and DD.MM.YYYY.
    The 'type' column is optional — defaults to 'buy' if absent.
    """
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"\n\nCSV file not found at:\n  {CSV_PATH}\n\n"
            "Please create it with columns: type,ticker,shares,price,date\n"
            "Example row:  buy,VHY,7,81.87,2026-03-30\n"
        )

    df = pd.read_csv(CSV_PATH)

    # Normalise column names — handle Title Case, lowercase, whitespace
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in ["ticker", "shares", "price", "date"] if c not in df.columns]
    if missing:
        raise ValueError(
            f"\n\nCSV is missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}\n"
            "Required: type, ticker, shares, price, date\n"
        )

    # 'type' column is optional — default to 'buy'
    if "type" not in df.columns:
        df["type"] = "buy"

    # Normalise values
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["type"]   = df["type"].astype(str).str.strip().str.lower()
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
    df["price"]  = pd.to_numeric(df["price"],  errors="coerce")

    # First-pass date parse: YYYY-MM-DD
    df["date"] = pd.to_datetime(df["date"], dayfirst=False, errors="coerce")
    mask_failed = df["date"].isna()
    if mask_failed.any():
        # Second-pass: DD.MM.YYYY
        raw_col = pd.read_csv(CSV_PATH).iloc[:, df.columns.tolist().index("date")]
        retry   = pd.to_datetime(raw_col, dayfirst=True, errors="coerce")
        df.loc[mask_failed, "date"] = retry[mask_failed]

    still_bad = (
        df["date"].isna().any()
        or df["shares"].isna().any()
        or df["price"].isna().any()
    )
    if still_bad:
        bad_rows = df[df[["date", "shares", "price"]].isna().any(axis=1)]
        raise ValueError(
            f"\n\nCSV has rows with invalid date, shares, or price:\n"
            f"{bad_rows.to_string()}\n\n"
            "Date format should be YYYY-MM-DD (e.g. 2026-03-30)\n"
        )

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    records = df[["type", "ticker", "shares", "price", "date"]].to_dict("records")
    logger.info("Loaded %d transactions from %s", len(records), CSV_PATH)
    return records


def save_csv(history: list[dict]) -> None:
    """
    Write the full transaction list back to CSV with automatic backup.
    
    Creates a backup (.bak) before write. If write fails, backup is restored.
    Raises exception on failure so caller can handle.
    """
    df = pd.DataFrame(history)[["type", "ticker", "shares", "price", "date"]]
    df.columns = ["Type", "Ticker", "Shares", "Price", "Date"]
    
    backup_path = f"{CSV_PATH}.bak"
    csv_dir = os.path.dirname(CSV_PATH)
    
    try:
        # Create backup of existing CSV if it exists
        if Path(CSV_PATH).exists():
            shutil.copy2(CSV_PATH, backup_path)
            logger.debug("Created backup at %s", backup_path)
        
        # Ensure directory exists
        os.makedirs(csv_dir, exist_ok=True)
        
        # Write new CSV
        df.to_csv(CSV_PATH, index=False)
        logger.info("Saved %d transactions to %s", len(history), CSV_PATH)
        
    except Exception as e:
        logger.error("Failed to write CSV at %s: %s", CSV_PATH, e)
        
        # Attempt recovery from backup
        if Path(backup_path).exists():
            try:
                shutil.copy2(backup_path, CSV_PATH)
                logger.info("Restored previous CSV from backup")
            except Exception as restore_err:
                logger.critical("Failed to restore from backup: %s", restore_err)
        
        raise
```

### data/portfolio_builder.py
```python
import logging
import pandas as pd
from config.constants import NAMES

logger = logging.getLogger(__name__)


def validate_transaction(txn: dict) -> tuple[bool, str]:
    """
    Validate transaction structure before aggregation.
    
    Returns:
        (is_valid, error_message)
    """
    required_keys = ["type", "ticker", "shares", "price", "date"]
    missing = [k for k in required_keys if k not in txn]
    if missing:
        return False, f"Transaction missing keys: {missing}"
    
    # Validate types
    try:
        shares = float(txn["shares"])
        price = float(txn["price"])
    except (TypeError, ValueError):
        return False, f"Shares and price must be numeric"
    
    if shares <= 0 or price <= 0:
        return False, f"Shares and price must be positive"
    
    txn_type = str(txn.get("type", "buy")).lower().strip()
    if txn_type not in ["buy", "sell"]:
        return False, f"Type must be 'buy' or 'sell', got '{txn_type}'"
    
    # Validate date format
    try:
        pd.to_datetime(str(txn["date"]), format="%Y-%m-%d")
    except (ValueError, TypeError):
        return False, f"Date must be YYYY-MM-DD, got '{txn['date']}'"
    
    return True, ""


def build_holdings(history: list[dict]) -> list[dict]:
    """
    Aggregate buy/sell transactions into one consolidated row per ticker.

    Returns a list of dicts, one per held ticker, with:
      - ticker, ticker_yf, name, market
      - total_shares (net after sells)
      - total_cost   (remaining cost at avg price)
      - avg_cost     (weighted avg of all buys)
      - first_purchase (earliest buy date string)
      - buy_tranches  (list of individual buy rows — needed for P&L history chart)
    """
    if not history:
        return []

    # Validate all transactions before processing
    invalid_txns = []
    for i, txn in enumerate(history):
        is_valid, error_msg = validate_transaction(txn)
        if not is_valid:
            invalid_txns.append((i, error_msg))
            logger.warning("Invalid transaction at index %d: %s", i, error_msg)
    
    if invalid_txns:
        logger.error("Found %d invalid transactions — skipping them", len(invalid_txns))

    # Filter out invalid transactions
    valid_history = [
        txn for i, txn in enumerate(history)
        if not any(idx == i for idx, _ in invalid_txns)
    ]

    if not valid_history:
        logger.warning("No valid transactions after validation")
        return []

    df = pd.DataFrame(valid_history)
    results = []

    for ticker, grp in df.groupby("ticker"):
        buys  = grp[grp["type"] == "buy"].copy()
        sells = (
            grp[grp["type"] == "sell"].copy()
            if "sell" in grp["type"].values
            else pd.DataFrame()
        )

        if buys.empty:
            continue

        total_bought = float(buys["shares"].sum())
        total_cost   = float((buys["shares"] * buys["price"]).sum())
        total_sold   = float(sells["shares"].sum()) if not sells.empty else 0.0
        net_shares   = total_bought - total_sold

        if net_shares <= 0:
            continue   # fully sold out — exclude from holdings

        avg_cost       = round(total_cost / total_bought, 4)
        # Proportional cost: preserves correct cost basis when shares are sold
        remaining_cost = round(total_cost * (net_shares / total_bought), 2)

        # Per-buy-tranche list — used by the P&L history chart
        buy_tranches = [
            {
                "ticker":    ticker,
                "shares":    float(r["shares"]),
                "price":     float(r["price"]),
                "date":      str(r["date"]),
                "buy_price": float(r["price"]),   # alias kept for chart compat
                "buy_date":  str(r["date"]),       # alias kept for chart compat
            }
            for _, r in buys.iterrows()
        ]

        results.append({
            "ticker":         ticker,
            "ticker_yf":      ticker + ".AX",
            "name":           NAMES.get(ticker, ticker),
            "market":         "ETF/ASX",
            "total_shares":   net_shares,
            "total_cost":     remaining_cost,
            "avg_cost":       avg_cost,
            "first_purchase": buys["date"].min(),
            "buy_tranches":   buy_tranches,
        })

    logger.info("Built %d holdings from %d transactions", len(results), len(history))
    return results
```