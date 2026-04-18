"""
callbacks/chart_callbacks.py
=============================
Chart callbacks.
"""

import logging
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html

from config.constants import COLORS, get_theme
from components.charts import (
    build_pnl_history_figure,
    build_price_chart_figure,
    build_allocation_figure,
    build_pnl_bar_figure,
    build_day_pnl_figure,
    build_dividend_figure,
    build_corr_figure,
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
        
        if not data or "holdings" not in data:
            return []
        tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
        return [
            html.Button(
                t,
                id={"type": "ticker-btn", "index": t},
                n_clicks=0,
                style={
                    "fontSize":     "12px",
                    "padding":      "4px 12px",
                    "borderRadius": "20px",
                    "cursor":       "pointer",
                    "fontWeight":   "500",
                    "background":   T_PRI if t == selected and t == "Portfolio" else (COLORS[(i - 1) % len(COLORS)] if t == selected else "transparent"),
                    "border": (
                        f"1.5px solid {T_PRI}"
                        if t == "Portfolio"
                        else f"1.5px solid {COLORS[(i - 1) % len(COLORS)]}"
                    ),
                    "color": BG if t == selected else (T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)]),
                },
            )
            for i, t in enumerate(tickers)
        ]

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

        if not data or "holdings" not in data:
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
        Input("period-picker",   "value"),
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
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("period-picker",     "value"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        # Allocation doesn't use period logically, but we receive it to re-trigger
        return build_allocation_figure(data["holdings"], t_)

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, period, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        # pnl_bar doesn't currently support period calculation
        return build_pnl_bar_figure(data["holdings"], mode, t_)

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        return build_day_pnl_figure(data["holdings"], t_)

    # ── Annual dividend income ────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart", "figure"),
        Input("portfolio-store", "data"),
        Input("period-picker",   "value"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, period, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        return build_dividend_figure(data["holdings"], t_)

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("period-picker",   "value"),
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