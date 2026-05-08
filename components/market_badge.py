# components/market_badge.py
"""
UI component for market status badge.
"""

from dash import html
from services.market.market_status import is_market_open

def market_badge() -> html.Span:
    """Render market status badge (follows official 10:00-16:00 hours)."""
    open_ = is_market_open(include_auction=False)
    return html.Span(
        "Open" if open_ else "Closed",
        id="market-badge",
        className=f"market-badge {'badge-open' if open_ else 'badge-closed'}",
    )
