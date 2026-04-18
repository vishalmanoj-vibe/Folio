"""
Charts Component Package.

Exports pure functions for generating Plotly figures from portfolio data.
"""

from .pnl_history import build_pnl_history_figure
from .price_history import build_price_chart_figure
from .allocation import build_allocation_figure
from .pnl_bar import build_pnl_bar_figure
from .day_pnl import build_day_pnl_figure
from .dividend import build_dividend_figure
from .correlation import build_corr_figure

__all__ = [
    "build_pnl_history_figure",
    "build_price_chart_figure",
    "build_allocation_figure",
    "build_pnl_bar_figure",
    "build_day_pnl_figure",
    "build_dividend_figure",
    "build_corr_figure",
]
