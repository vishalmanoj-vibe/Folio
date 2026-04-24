"""
callbacks/chart_callbacks.py
=============================
Chart callbacks.
"""

import logging
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html
import dash_mantine_components as dmc

from config.constants import COLORS, get_theme
from components.ui_helpers import chart_skeleton
from components.charts import (
    build_pnl_history_figure,
    build_price_chart_figure,
    build_corr_figure,
    build_portfolio_treemap,
    build_performance_lollipops,
    build_intel_volatility_chart,
)
from components.charts.intel_helpers import create_empty_fig
from services.intelligence_service import (
    compute_risk_metrics,
    fetch_etf_sector_weights,
    fetch_etf_geo_weights,
)

logger = logging.getLogger(__name__)

def register_callbacks(app) -> None:
    """
    Register chart-related callbacks with the Dash application.
    """

    # ── Ticker selector options ───────────────────────────────────────────────
    @app.callback(
        Output("ticker-selector", "data"),
        Input("portfolio-store",  "data"),
    )
    def update_ticker_options(data):
        if not data or "holdings" not in data or not data["holdings"]:
            return ["Portfolio"]
        
        tickers = ["Portfolio"] + sorted([h["ticker"] for h in data["holdings"]])
        return [{"label": t, "value": t} for t in tickers]


    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        Input("period-store",       "data"),
        Input("pnl-mode-store",     "data"),
        Input("ticker-store",       "data"),
    )
    def pnl_history_chart(data, theme, period, mode, selected):
        t_       = get_theme(theme or "dark")
        period   = period or "max"
        mode     = mode or "pct"
        selected = selected or "Portfolio"

        if not data or "holdings" not in data or not data["holdings"]:
            return create_empty_fig("No holdings data available", height=450, theme_tokens=t_)

        return build_pnl_history_figure(data["holdings"], mode, period, t_, selected)

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
        Input("analytics-period-store", "data"),
    )
    def price_chart(data, theme, period):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            return create_empty_fig("No price history available", height=400, theme_tokens=t_)
        holdings = data.get("holdings", [])
        return build_price_chart_figure(data["histories"], period, t_, holdings)

    # ── Portfolio Treemap ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-treemap", "figure"),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        Input("treemap-mode-store", "data"),
    )
    def portfolio_treemap(data, theme, mode):
        t_ = get_theme(theme or "dark")
        mode = mode or "sector"
        if not data or "holdings" not in data or not data["holdings"]:
            return create_empty_fig("No holdings data available", height=450, theme_tokens=t_)
        
        mode = mode or "sector"
        sector_map = {}
        geo_map = {}
        
        if mode == "sector":
            for h in data["holdings"]:
                ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
                sector_map[h["ticker"]] = fetch_etf_sector_weights(ticker_yf)
        elif mode == "geo":
            for h in data["holdings"]:
                ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
                geo_map[h["ticker"]] = fetch_etf_geo_weights(ticker_yf)
            
        return build_portfolio_treemap(
            data["holdings"], t_, 
            mode=mode, 
            sector_data=sector_map, 
            geo_data=geo_map
        )


    # ── Analytics Risk ────────────────────────────────────────────────────────
    @app.callback(
        Output("analytics-vol-chart",    "figure"),
        Input("portfolio-store",         "data"),
        Input("theme-store",             "data"),
        Input("analytics-period-store", "data"),
    )
    def update_analytics_volatility(data, theme, period):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "holdings" not in data or not data["holdings"]:
            from components.charts.intel_helpers import create_empty_fig, _BAR_MIN_H
            return create_empty_fig(height=_BAR_MIN_H, bar=True, theme_tokens=t_)

        metrics = compute_risk_metrics(data, period=(period or "max"))
        return build_intel_volatility_chart(metrics.get("ticker_vols", {}), t_)

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
        Input("analytics-period-store", "data"),
    )
    def update_corr_chart(data, theme, period):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            return create_empty_fig("No shared history found", height=380, theme_tokens=t_)
        return build_corr_figure(data["histories"], period, t_)