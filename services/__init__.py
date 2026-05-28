# services/__init__.py
"""
Services layer for Folio.

Business logic for market data, alerts, and portfolio operations.
"""

from services.alert_service import check_alerts
from services.market import fetch_live, is_market_open

__all__ = [
    "fetch_live",
    "is_market_open",
    "check_alerts",
]
