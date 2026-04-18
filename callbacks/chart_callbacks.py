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
    )
    def build_toggle_btns(data, theme):
        t_    = get_theme(theme or "dark")
        T_PRI = t_["T_PRI"]
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
                    "background":   "transparent",
                    "border": (
                        f"1.5px solid {T_PRI}"
                        if t == "Portfolio"
                        else f"1.5px solid {COLORS[(i - 1) % len(COLORS)]}"
                    ),
                    "color": T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)],
                },
            )
            for i, t in enumerate(tickers)
        ]

    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("pnl-mode",           "value"),
        Input("period-picker",      "value"),
        Input("theme-store",        "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State({"type": "ticker-btn", "index": ALL}, "id"),
    )
    def pnl_history_chart(data, mode, period, theme, n_clicks_list, btn_ids):
        t_     = get_theme(theme or "dark")
        period = period or "max"

        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(
                xaxis=dict(showgrid=False, type="date"),
                yaxis=dict(gridcolor=t_["BORDER"], zerolinecolor=t_["BORDER"]),
                **t_["PLOTLY_BASE"]
            )
            return fig

        selected = "Portfolio"
        if n_clicks_list and any(n and n > 0 for n in n_clicks_list):
            last_idx = max(range(len(n_clicks_list)), key=lambda i: n_clicks_list[i] or 0)
            selected = btn_ids[last_idx]["index"]

        return build_pnl_history_figure(data["holdings"], mode, period, t_, selected)

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, theme):
        t_ = get_theme(theme or "dark")
        if not data or "histories" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        return build_price_chart_figure(data["histories"], t_)

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        return build_allocation_figure(data["holdings"], t_)

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, theme):
        t_ = get_theme(theme or "dark")
        if not data or "holdings" not in data:
            fig = go.Figure()
            fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=t_["BORDER"]), **t_["PLOTLY_BASE"])
            return fig
        return build_pnl_bar_figure(data["holdings"], mode, t_)

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, theme):
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
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, theme):
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
        Input("theme-store",     "data"),
    )
    def corr_chart(data, theme):
        t_ = get_theme(theme or "dark")
        if not data or "histories" not in data:
            fig = go.Figure()
            fig.update_layout(**t_["PLOTLY_BASE"])
            return fig
        return build_corr_figure(data["histories"], t_)