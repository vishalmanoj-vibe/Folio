"""
callbacks/chart_callbacks.py
=============================
Thin orchestration layer — no pandas, no chart logic, no business math.

All figure construction is delegated to components/charts.py.
Selected-ticker state is persisted in selected-ticker-store so chart
selection survives portfolio-store refreshes.
"""

from dash import Input, Output, State, ALL, ctx

from config.constants import get_theme
from components.charts import (
    build_toggle_buttons,
    build_pnl_history_figure,
    build_price_chart_figure,
    build_allocation_figure,
    build_pnl_bar_figure,
    build_day_pnl_figure,
    build_dividend_figure,
    build_corr_figure,
)


def register_callbacks(app) -> None:

    # ── Persist selected ticker on button click ───────────────────────────────
    @app.callback(
        Output("selected-ticker-store", "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State({"type": "ticker-btn", "index": ALL}, "id"),
        State("selected-ticker-store", "data"),
        prevent_initial_call=True,
    )
    def persist_selected_ticker(n_clicks_list, btn_ids, current):
        if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict):
            return current or "Portfolio"
        return ctx.triggered_id["index"]

    # ── Ticker toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("ticker-toggle-btns",    "children"),
        Input("portfolio-store",        "data"),
        Input("selected-ticker-store",  "data"),
        Input("theme-store",            "data"),
    )
    def update_toggle_buttons(data, selected, theme):
        if not data or "holdings" not in data:
            return []
        return build_toggle_buttons(
            holdings=data["holdings"],
            selected=selected or "Portfolio",
            theme_tokens=get_theme(theme or "dark"),
        )

    # ── P&L history chart ─────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart",    "figure"),
        Input("portfolio-store",       "data"),
        Input("pnl-mode",              "value"),
        Input("theme-store",           "data"),
        Input("selected-ticker-store", "data"),
    )
    def pnl_history_chart(data, mode, theme, selected):
        if not data or "holdings" not in data:
            return build_pnl_history_figure([], mode, get_theme(theme or "dark"))
        return build_pnl_history_figure(
            holdings=data["holdings"],
            mode=mode,
            theme_tokens=get_theme(theme or "dark"),
            selected=selected or "Portfolio",
        )

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, theme):
        histories = (data or {}).get("histories", {})
        return build_price_chart_figure(histories, get_theme(theme or "dark"))

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, theme):
        if not data or "holdings" not in data:
            return build_allocation_figure([], get_theme(theme or "dark"))
        return build_allocation_figure(data["holdings"], get_theme(theme or "dark"))

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, theme):
        if not data or "holdings" not in data:
            return build_pnl_bar_figure([], mode, get_theme(theme or "dark"))
        return build_pnl_bar_figure(data["holdings"], mode, get_theme(theme or "dark"))

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, theme):
        if not data or "holdings" not in data:
            return build_day_pnl_figure([], get_theme(theme or "dark"))
        return build_day_pnl_figure(data["holdings"], get_theme(theme or "dark"))

    # ── Annual dividend bar ───────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart", "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, theme):
        if not data or "holdings" not in data:
            return build_dividend_figure([], get_theme(theme or "dark"))
        return build_dividend_figure(data["holdings"], get_theme(theme or "dark"))

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def corr_chart(data, theme):
        histories = (data or {}).get("histories", {})
        return build_corr_figure(histories, get_theme(theme or "dark"))