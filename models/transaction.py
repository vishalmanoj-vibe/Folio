# models/transaction.py
"""
Data models for Folio.

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
