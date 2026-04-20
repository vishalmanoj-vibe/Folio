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
    build_allocation_figure,
    build_pnl_bar_figure,
    build_day_pnl_figure,
    build_dividend_figure,
    build_corr_figure,
)
from components.charts.mantine_charts import (
    create_pnl_bar_dmc,
    create_day_pnl_dmc,
    create_allocation_dmc,
    create_dividend_dmc
)

logger = logging.getLogger(__name__)

def register_callbacks(app) -> None:
    """
    Register chart-related callbacks with the Dash application.

    Handles building and updating all Plotly charts based on user interactions
    and portfolio state changes.

    Args:
        app: The Dash application instance.
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
            
            # Base color for the button
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
            
        # Ignore if the trigger was a recreation of buttons (n_clicks=0 or None)
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
            # We return an empty figure with a hidden skeleton (handled via dcc.Loading or similar)
            # But here we just return a blank figure to avoid errors
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

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart-container", "children"),
        Input("portfolio-store",   "data"),
        Input("analytics-period-picker",     "value"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, period, theme):
        if not data or "holdings" not in data or not data["holdings"]:
            return chart_skeleton(height=280)
        return create_allocation_dmc(data["holdings"])

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart-container",  "children"),
        Input("portfolio-store", "data"),
        Input("analytics-pnl-mode",        "value"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, period, theme):
        if not data or "holdings" not in data or not data["holdings"]:
            return chart_skeleton(height=280)
        return create_pnl_bar_dmc(data["holdings"], mode)

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart-container",  "children"),
        Input("portfolio-store", "data"),
        Input("analytics-pnl-mode",        "value"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, mode, period, theme):
        if not data or "holdings" not in data or not data["holdings"]:
            return chart_skeleton(height=280)
        return create_day_pnl_dmc(data["holdings"], mode)

    # ── Annual dividend income ────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart-container", "children"),
        Input("portfolio-store", "data"),
        Input("analytics-pnl-mode",        "value"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, mode, period, theme):
        if not data or "holdings" not in data or not data["holdings"]:
            return chart_skeleton(height=280)
        return create_dividend_dmc(data["holdings"])

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("analytics-period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def corr_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "histories" not in data:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        return build_corr_figure(data["histories"], period, t_)