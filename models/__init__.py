# models/__init__.py
"""
Portfolio models for Folio.

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
