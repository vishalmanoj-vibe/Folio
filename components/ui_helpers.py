# components/ui_helpers.py
"""
components/ui_helpers.py
=========================
Refined UI helpers for the Folio Dashboard.
"""

from typing import Any, cast

import dash_mantine_components as dmc
import pandas as pd
from dash import html

from config.constants import CHART_INFO, COLORS


def interpolate_color(start_hex: str, end_hex: str, fraction: float) -> str:
    """Linearly interpolates between two hex colors based on a fraction (0 to 1)."""
    s = start_hex.lstrip("#")
    e = end_hex.lstrip("#")

    # Standard hex to RGB
    r1, g1, b1 = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    r2, g2, b2 = int(e[0:2], 16), int(e[2:4], 16), int(e[4:6], 16)

    # LERP (Linear Interpolation)
    r = int(r1 + (r2 - r1) * fraction)
    g = int(g1 + (g2 - g1) * fraction)
    b = int(b1 + (b2 - b1) * fraction)

    return f"#{r:02x}{g:02x}{b:02x}"


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = "var(--t-pri)",
    sub_color: str = "var(--t-sec)",
    tip: str = "",
) -> html.Div:
    """Creates a styled stat card component."""
    label_children: list = [html.Span(label, className="stat-card-title")]
    if tip:
        label_children.append(
            dmc.Tooltip(
                label=tip,
                multiline=True,
                w=240,
                withArrow=True,
                transitionProps=cast(Any, {"transition": "fade", "duration": 200}),
                position="top",
                zIndex=2000,
                children=html.Span("ℹ", className="chart-info-icon"),
            )
        )
    children = [
        html.Div(label_children, className="stat-card-label-row"),
        html.P(value, className="stat-card-value", style={"color": color}),
    ]
    if sub:
        children.append(html.P(sub, className="stat-card-sub", style={"color": sub_color}))

    return html.Div(children, className="stat-card-container")


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Creates a clean chart title with an optional help icon."""
    if info_key and info_key in CHART_INFO:
        tip = CHART_INFO[info_key][1]
    else:
        tip = info_key

    children: list = [html.Span(label, className="chart-title-text")]
    if tip:
        children.append(
            dmc.Tooltip(
                label=tip,
                multiline=True,
                w=280,
                withArrow=True,
                transitionProps=cast(Any, {"transition": "fade", "duration": 200}),
                position="top",
                zIndex=2000,
                children=html.Span("ℹ", className="chart-info-icon"),
            )
        )

    return html.Div(children, className="chart-title-container")


def section(title_node: Any, children) -> html.Div:
    """Standard section wrapper."""
    content = [title_node, children] if title_node is not None else [children]
    return html.Div(content, className="section-container")


def alert_card(alert: dict) -> html.Div:
    """Creates a themed smart alert card for the Intelligence dashboard."""
    level = alert.get("level", "info")
    # Map 'danger' to 'danger', 'warning' to 'warning', 'info' to 'info', 'ok' to 'ok'
    # These match the CSS classes in base.css
    return html.Div(
        [
            html.Span(alert.get("icon", "ℹ"), className="alert-icon"),
            html.Div(
                [
                    html.Div(alert.get("title", ""), className="smart-alert-title"),
                    html.Div(alert.get("detail", ""), className="smart-alert-detail"),
                ]
            ),
        ],
        className=f"smart-alert {level}",
    )


def txn_table(history: list[dict]) -> html.Div:
    """Renders the transaction history table with deep-linking to positions."""
    if not history:
        return html.P("No transactions yet.", className="txn-empty")

    rows = [
        html.Tr(
            [
                html.Td(t["date"], className="table-td"),
                html.Td(
                    html.A(t["ticker"], href="/positions", className="ticker-link"),
                    className="table-td",
                    style={"fontWeight": "500"},
                ),
                html.Td(
                    t["type"].upper(),
                    className="table-td",
                    style={
                        "color": "var(--green)" if t["type"] == "buy" else "var(--red)",
                        "fontWeight": "600",
                    },
                ),
                html.Td(f"{float(t['shares']):g}", className="table-td"),
                html.Td(f"${float(t['price']):,.3f}", className="table-td"),
                html.Td(f"${float(t['shares']) * float(t['price']):,.2f}", className="table-td"),
            ]
        )
        for t in reversed(history)
    ]

    return html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th(c, className="table-th")
                        for c in ["Date", "Ticker", "Type", "Shares", "Price", "Total"]
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        className="table-container",
    )


def stat_card_skeleton() -> html.Div:
    """Pulsing placeholder for a stat card"""
    return html.Div(
        [
            html.Div(
                html.Div(className="skeleton", style={"height": "10px", "width": "40%"}),
                className="stat-card-label-row",
            ),
            html.Div(
                className="skeleton", style={"height": "28px", "width": "80%", "marginTop": "6px"}
            ),
            html.Div(
                className="skeleton", style={"height": "12px", "width": "60%", "marginTop": "10px"}
            ),
        ],
        className="stat-card-container",
    )


def risk_card_skeleton() -> html.Div:
    """Pulsing placeholder for a risk card in Intelligence page"""
    return html.Div(
        [
            html.Div(
                className="skeleton",
                style={"height": "10px", "width": "50%", "marginBottom": "8px"},
            ),
            html.Div(className="skeleton", style={"height": "24px", "width": "70%"}),
            html.Div(
                className="skeleton", style={"height": "10px", "width": "40%", "marginTop": "8px"}
            ),
        ],
        className="etf-detail-card",  # Using same class as metrics for consistency
        style={"minWidth": "140px"},
    )


def table_skeleton(rows: int = 5) -> html.Div:
    """Pulsing placeholder for a table"""
    return html.Div(
        [
            # Header
            html.Div(
                className="skeleton",
                style={"height": "32px", "width": "100%", "marginBottom": "8px", "opacity": "0.6"},
            ),
            # Rows
            *[
                html.Div(
                    className="skeleton",
                    style={"height": "32px", "width": "100%", "marginBottom": "4px"},
                )
                for _ in range(rows)
            ],
        ],
        style={
            "padding": "12px",
            "background": "var(--surface-2)",
            "borderRadius": "8px",
            "border": "0.5px solid var(--border)",
        },
    )


def chart_skeleton(height: int = 300) -> html.Div:
    """Pulsing placeholder for a chart"""
    return html.Div(
        className="skeleton",
        style={"height": f"{height}px", "width": "100%", "borderRadius": "10px"},
    )


def progress_row(
    ticker: str,
    value: float,
    max_val: float,
    prefix: str = "",
    suffix: str = "",
    color: str = "var(--cyan)",
) -> html.Div:
    """
    Creates a premium-styled horizontal progress row with label, bar, and value.
    Commonly used for ranking ETFs by income or yield.
    """
    percent = (value / max_val * 100) if max_val > 0 else 0
    fmt = ",.2f"
    return html.Div(
        [
            html.Div(ticker, className="progress-ticker"),
            html.Div(
                dmc.Progress(
                    value=percent,
                    color=color,
                    size="lg",
                    radius="xl",
                    className="progress-bar-component",
                ),
                className="progress-bar-wrapper",
            ),
            html.Div(f"{prefix}{value:{fmt}}{suffix}", className="progress-value"),
        ],
        className="progress-row",
    )


def tech_signal_badges(ticker: str, history: list[dict] | pd.Series) -> html.Div:
    """Renders a row of technical signal badges for a given ticker."""
    from services.technical_indicators import compute_signals

    # Unified empty check for list or Series
    is_empty = False
    if history is None:
        is_empty = True
    elif isinstance(history, pd.Series):
        is_empty = history.empty
    elif isinstance(history, list):
        is_empty = len(history) == 0

    if is_empty:
        return html.Div(
            "Insufficient history for technicals.",
            style={"color": "var(--t-sec)", "fontSize": "12px", "padding": "8px 0"},
        )

    sig = compute_signals(ticker, history)
    if "error" in sig:
        return html.Div(
            "Error computing technicals.",
            style={"color": "var(--t-sec)", "fontSize": "12px", "padding": "8px 0"},
        )

    # Styling for badges
    rsi_color = (
        "var(--green)"
        if sig["rsi_label"] == "Oversold"
        else "var(--red)"
        if sig["rsi_label"] == "Overbought"
        else "var(--t-sec)"
    )
    macd_color = (
        "var(--green)"
        if sig["macd_label"] == "Bullish"
        else "var(--red)"
        if sig["macd_label"] == "Bearish"
        else "var(--t-sec)"
    )
    bb_color = "var(--t-sec)"

    # SMA 200 color
    sma_color = (
        "var(--green)"
        if sig["sma_label"] == "Bullish"
        else "var(--red)"
        if sig["sma_label"] == "Bearish"
        else "var(--t-sec)"
    )

    # Volatility color
    vol_color = (
        "var(--green)"
        if sig["vol_label"] == "Low"
        else "var(--red)"
        if sig["vol_label"] == "High"
        else "var(--t-sec)"
    )

    def badge(label, value, color, tip):
        return dmc.Tooltip(
            label=tip,
            multiline=True,
            w=240,
            withArrow=True,
            transitionProps=cast(Any, {"transition": "fade", "duration": 200}),
            position="top",
            zIndex=2000,
            children=html.Div(
                [
                    html.Span(
                        f"{label}: ", style={"color": "var(--t-sec)", "fontWeight": "normal"}
                    ),
                    html.Span(value, style={"color": color, "fontWeight": "bold"}),
                ],
                className="tech-badge",
                style={"border": f"0.5px solid {color}"},
            ),
        )

    return html.Div(
        [
            badge(
                "RSI",
                f"{sig['rsi']:.1f} ({sig['rsi_label']})",
                rsi_color,
                "Relative Strength Index (RSI): Measures price momentum. Values > 70 suggest 'Overbought' (potentially expensive), while < 30 suggest 'Oversold' (potentially undervalued).",
            ),
            badge(
                "MACD",
                sig["macd_label"],
                macd_color,
                "MACD: A momentum indicator that signals trend shifts. 'Bullish' means upward momentum is building; 'Bearish' warns of increasing downward pressure.",
            ),
            badge(
                "BB",
                sig["bb_label"],
                bb_color,
                "Bollinger Bands (BB): Measures volatility relative to a 20-day average. Touching the upper band suggests price is overextended; the lower band suggests it is statistically cheap.",
            ),
            badge(
                "Trend",
                sig["sma_label"],
                sma_color,
                "200-Day SMA: The 'Golden Line' for long-term trends. Staying above this line confirms a healthy Bull market; dropping below is a primary warning of a long-term Bear market.",
            ),
            badge(
                "Vol",
                sig["vol_label"],
                vol_color,
                "Annualized Volatility: Measures daily price swings over the last 30 days. Low (<15%) is stable; High (>30%) warns of significant daily risk and large price fluctuations.",
            ),
        ],
        style={"display": "flex", "flexWrap": "wrap", "gap": "8px", "margin": "12px 0"},
    )
