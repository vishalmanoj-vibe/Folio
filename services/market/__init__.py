# services/market/__init__.py
"""
Market services for Folio.

Market data fetching and status checking.
"""

from services.market.data_fetcher import fetch_live
from services.market.market_status import is_market_open

__all__ = [
    "fetch_live",
    "is_market_open",
]
