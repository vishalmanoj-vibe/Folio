"""
components/ui_helpers.py
=========================
Refined UI helpers. Keeps the original clean aesthetic you prefer, with small polish:
- Better spacing and typography on stat cards
- Improved transaction history table (clickable tickers, better alignment)
- Cleaner chart titles
"""

from dash import html
from config.constants import GREEN, RED, COLORS, CHART_INFO

# Alert level styling
_LEVEL_COLOR = {"danger": "var(--danger)", "warning": "var(--warning)", "info":  "var(--info)"}
_LEVEL_BG    = {
    "danger":  "rgba(226,75,74,0.08)",
    "warning": "rgba(239,159,39,0.08)",
    "info":    "rgba(55,138,221,0.08)",
}


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = "var(--t-pri)",
    sub_color: str = "var(--t-sec)",
    tip: str = "",
) -> html.Div:
    """Stat card with optional ℹ tooltip on the label."""
    label_children = [html.Span(label, className="stat-card-title")]
    if tip:
        label_children.append(
            html.Span("ℹ", title=tip, className="chart-info-icon")
        )
    return html.Div(
        [
            html.Div(label_children, className="stat-card-label-row"),
            html.P(value, className="stat-card-value", style={"color": color}),
            html.P(sub, className="stat-card-sub", style={"color": sub_color}) if sub else None,
        ],
        className="stat-card stat-card-container",
    )


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Clean chart title with improved info icon"""
    if info_key and info_key in CHART_INFO:
        tip = CHART_INFO[info_key][1]
    else:
        tip = info_key
    
    children = [html.Span(label, className="chart-title-text")]
    
    if tip:
        children.append(
            html.Span("ℹ", title=tip, className="chart-info-icon")
        )
    
    return html.Div(children, className="chart-title-container")


def section(title_node: html.Div, children) -> html.Div:
    """Original section style"""
    return html.Div(
        [title_node, children],
        className="section-container",
    )


def alert_card(alert: dict) -> html.Div:
    level = alert.get("level", "info")
    color = _LEVEL_COLOR.get(level, COLORS[0])
    bg    = _LEVEL_BG.get(level, "rgba(55,138,221,0.08)")
    return html.Div(
        html.Div([
            html.Span(alert.get("icon", "ℹ"), className="alert-icon"),
            html.Div([
                html.Span(alert.get("title", ""), className="alert-title", style={"color": color}),
                html.Span("  —  " + alert.get("detail", ""), className="alert-detail"),
            ]),
        ], className="alert-content"),
        className="alert-container",
        style={"background": bg, "border": f"0.5px solid {color}"},
    )


def txn_table(history: list[dict]) -> html.Element:
    """Polished transaction table - same style as original but better readability"""
    if not history:
        return html.P("No transactions yet.", className="txn-empty")

    rows = [
        html.Tr([
            html.Td(t["date"], className="table-td"),
            html.Td(
                html.A(t["ticker"], href=f"/etf/{t['ticker']}", className="ticker-link"),
                className="table-td", style={"fontWeight": "500"}
            ),
            html.Td(
                t["type"].upper(),
                className="table-td",
                style={"color": "var(--green)" if t["type"] == "buy" else "var(--red)", "fontWeight": "600"}
            ),
            html.Td(f"{float(t['shares']):,.2f}", className="table-td"),
            html.Td(f"${float(t['price']):,.4f}", className="table-td"),
            html.Td(f"${float(t['shares']) * float(t['price']):,.2f}", className="table-td"),
        ])
        for t in reversed(history)
    ]

    return html.Table(
        [
            html.Thead(html.Tr([html.Th(c, className="table-th") for c in ["Date", "Ticker", "Type", "Shares", "Price", "Total"]])),
            html.Tbody(rows),
        ],
        className="table-container",
    )


def stat_card_skeleton() -> html.Div:
    """Pulsing placeholder for a stat card"""
    import dash_mantine_components as dmc
    return html.Div(
        [
            html.Div(dmc.Skeleton(height=14, width="40%", radius="sm"), className="stat-card-label-row"),
            dmc.Skeleton(height=28, width="80%", radius="sm", style={"marginTop": "8px"}),
            dmc.Skeleton(height=14, width="60%", radius="sm", style={"marginTop": "10px"}),
        ],
        className="stat-card stat-card-container",
    )


def table_skeleton(rows: int = 5, cols: int = 6) -> html.Div:
    """Pulsing placeholder for a table"""
    import dash_mantine_components as dmc
    return html.Div(
        [
            html.Div(
                [dmc.Skeleton(height=35, radius="sm", style={"marginBottom": "8px"}) for _ in range(rows + 1)],
                style={"padding": "12px"}
            )
        ],
        style={"overflowX": "auto", "borderRadius": "8px", "border": "0.5px solid var(--border)", "background": "var(--surface)"},
    )


def chart_skeleton(height: int = 300) -> dmc.Skeleton:
    """Pulsing placeholder for a chart"""
    import dash_mantine_components as dmc
    return dmc.Skeleton(height=height, radius="sm", style={"width": "100%"})