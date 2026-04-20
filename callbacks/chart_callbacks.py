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

    # ── Ticker toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("ticker-toggle-btns", "children"),
        Input("portfolio-store",     "data"),
        Input("theme-store",         "data"),
        Input("selected-ticker-store", "data"),
    )
    def build_toggle_btns(data, theme, selected):
        t_    = get_theme(theme or "dark")
        T_PRI = t_["T_PRI"]
        BG    = t_["BG"]
        selected = selected or "Portfolio"
        
        if not data or "holdings" not in data or not data["holdings"]:
            return []
        tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
        btns = []
        for i, t in enumerate(tickers):
            is_sel = (t == selected)
            is_port = (t == "Portfolio")
            
            c = T_PRI if is_port else COLORS[(i - 1) % len(COLORS)]
            
            style = {
                "fontSize":     "12px",
                "padding":      "4px 12px",
                "borderRadius": "20px",
                "cursor":       "pointer",
                "fontWeight":   "500",
                "transition":   "all 0.15s ease",
                "background":   c if is_sel else "transparent",
                "color":        BG if is_sel else c,
                "border":       f"1.5px solid {c}",
            }
            
            btns.append(html.Button(
                t,
                id={"type": "ticker-btn", "index": t},
                n_clicks=0,
                style=style
            ))
        return btns

    # ── Selected Ticker State ─────────────────────────────────────────────────
    @app.callback(
        Output("selected-ticker-store", "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State("selected-ticker-store", "data"),
        prevent_initial_call=True,
    )
    def update_selected_ticker(n_clicks_list, current_selected):
        import dash
        import json
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
            
        if not ctx.triggered[0]["value"]:
            raise dash.exceptions.PreventUpdate
            
        try:
            trigger_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
            return trigger_id["index"]
        except Exception:
            return current_selected

    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("pnl-mode",           "value"),
        Input("period-picker",      "value"),
        Input("theme-store",        "data"),
        Input("selected-ticker-store", "data"),
    )
    def pnl_history_chart(data, mode, period, theme, selected):
        t_     = get_theme(theme or "dark")
        period = period or "max"
        selected = selected or "Portfolio"

        if not data or "holdings" not in data or not data["holdings"]:
            fig = go.Figure()
            fig.update_layout(
                xaxis=dict(showgrid=False, type="date"),
                yaxis=dict(gridcolor=t_["BORDER"], zerolinecolor=t_["BORDER"]),
                **t_["PLOTLY_BASE"]
            )
            return fig

        return build_pnl_history_figure(data["holdings"], mode, period, t_, selected)

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        holdings = data.get("holdings", [])
        return build_price_chart_figure(data["histories"], period, t_, holdings)

    # ── Portfolio Treemap ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-treemap", "figure"),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        Input("treemap-mode",       "value"),
    )
    def portfolio_treemap(data, theme, mode):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data or not data["holdings"]:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        
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

    # ── Dividend Lollipops ─────────────────────────────────────────────────────
    @app.callback(
        Output("dividend-lollipops", "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store", "data"),
    )
    def dividend_lollipops(data, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data or not data["holdings"]:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
            
        plot_data = []
        for h in data["holdings"]:
            val = h.get("annual_div", 0)
            if val > 0:
                plot_data.append({"ticker": h["ticker"], "value": val})
            
        return build_performance_lollipops(plot_data, t_, "dollar")

    # ── Analytics Risk ────────────────────────────────────────────────────────
    @app.callback(
        Output("analytics-vol-chart",    "figure"),
        Input("portfolio-store",         "data"),
        Input("analytics-period-picker", "value"),
        Input("theme-store",             "data"),
    )
    def update_analytics_volatility(data, period, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data or not data["holdings"]:
            from components.charts.intel_helpers import create_empty_fig, _BAR_MIN_H
            return create_empty_fig(height=_BAR_MIN_H, bar=True, theme_tokens=t_)

        metrics = compute_risk_metrics(data, period=(period or "max"))
        return build_intel_volatility_chart(metrics.get("ticker_vols", {}), t_)

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def update_corr_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        return build_corr_figure(data["histories"], period, t_)