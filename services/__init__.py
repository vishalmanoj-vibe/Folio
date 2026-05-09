# services/__init__.py
"""
Services layer for Folio.

Business logic for market data, alerts, and portfolio operations.
"""

from services.market import fetch_live, is_market_open
from services.alert_service import check_alerts

__all__ = [
    "fetch_live",
    "is_market_open",
    "check_alerts",
]
