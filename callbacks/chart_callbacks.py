# callbacks/chart_callbacks.py
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
from components.charts import (
    build_pnl_history_figure,
    build_price_chart_figure,
    build_corr_figure,
    build_portfolio_treemap,
    build_performance_lollipops,
)
from components.ui_helpers import chart_skeleton, progress_row, interpolate_color
from components.charts.helpers import create_empty_fig
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
        Input("url","pathname"),
    )
    def update_ticker_options(data, pathname):
        import dash
        if pathname != "/": return dash.no_update
        if not data or "holdings" not in data or not data["holdings"]:
            return ["Portfolio"]
        
        tickers = ["Portfolio"] + sorted([h["ticker"] for h in data["holdings"]])
        return [{"label": t, "value": t} for t in tickers]


    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        # FIX: change to State to prevent double-rendering when portfolio-store updates
        State("period-store",       "data"),
        Input("pnl-mode-store",     "data"),
        Input("ticker-store",       "data"),
        Input("url",                "pathname"),
    )
    def pnl_history_chart(data, theme, period, mode, selected, pathname):
        import dash
        if pathname != "/": return dash.no_update
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
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",             "pathname"),
    )
    def price_chart(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
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
        Input("url",                "pathname"),
    )
    def portfolio_treemap(data, theme, mode, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
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
        Output("analytics-vol-chart",    "children"),
        Input("portfolio-store",         "data"),
        Input("theme-store",             "data"),
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",                     "pathname"),
    )
    def update_analytics_volatility(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        if not data or "holdings" not in data or not data["holdings"]:
            return html.P("No holdings data available", style={"color": "var(--t-sec)", "fontSize": "13px"})

        metrics = compute_risk_metrics(data, period=(period or "max"))
        ticker_vols = metrics.get("ticker_vols", {})
        
        if not ticker_vols:
            return html.P("Insufficient data for this period", style={"color": "var(--t-sec)", "fontSize": "13px"})

        # Sort descending (Highest volatility first)
        tv = sorted(
            [(t, v) for t, v in ticker_vols.items() if v is not None],
            key=lambda x: x[1],
            reverse=True
        )
        
        if not tv:
            return html.P("No volatility metrics available", style={"color": "var(--t-sec)", "fontSize": "13px"})

        max_vol = max([v for _, v in tv]) if tv else 0
        n_vols = len(tv)
        
        # Red (High) -> Yellow (Mid) -> Green (Low)
        C_RED    = "#E24B4A"
        C_YELLOW = "#EF9F27"
        C_GREEN  = "#1D9E75"

        rows = []
        for i, (ticker, val) in enumerate(tv):
            if n_vols > 1:
                fraction = i / (n_vols - 1)
                if fraction < 0.5:
                    # Interpolate Red to Yellow (0.0 to 0.5)
                    local_frac = fraction / 0.5
                    color = interpolate_color(C_RED, C_YELLOW, local_frac)
                else:
                    # Interpolate Yellow to Green (0.5 to 1.0)
                    local_frac = (fraction - 0.5) / 0.5
                    color = interpolate_color(C_YELLOW, C_GREEN, local_frac)
            else:
                color = C_RED

            rows.append(
                progress_row(ticker, val, max_vol, suffix="%", color=color)
            )
        return rows

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",             "pathname"),
    )
    def update_corr_chart(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            return create_empty_fig("No shared history found", height=380, theme_tokens=t_)
        return build_corr_figure(data["histories"], period, t_)