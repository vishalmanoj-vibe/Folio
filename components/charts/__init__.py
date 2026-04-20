"""
Charts Component Package.

Exports pure functions for generating Plotly figures from portfolio data.
"""

from .pnl_history import build_pnl_history_figure
from .price_history import build_price_chart_figure
from .correlation import build_corr_figure
from .treemap import build_portfolio_treemap
from .performance_bars import build_performance_lollipops
from .intel_volatility import build_intel_volatility_chart

__all__ = [
    "build_pnl_history_figure",
    "build_price_chart_figure",
    "build_corr_figure",
    "build_portfolio_treemap",
    "build_performance_lollipops",
    "build_intel_volatility_chart",
]
