"""
components/ui_helpers.py
=========================
Refined UI helpers for the Portfolio Dashboard.
"""

from dash import html
import dash_mantine_components as dmc
from config.constants import COLORS, CHART_INFO

def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = "var(--t-pri)",
    sub_color: str = "var(--t-sec)",
    tip: str = "",
) -> html.Div:
    """Creates a styled stat card component."""
    label_children = [html.Span(label, className="stat-card-title")]
    if tip:
        label_children.append(
            html.Span("ℹ", title=tip, className="chart-info-icon")
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
    
    children = [html.Span(label, className="chart-title-text")]
    if tip:
        children.append(html.Span("ℹ", title=tip, className="chart-info-icon"))
    
    return html.Div(children, className="chart-title-container")

def section(title_node: html.Div | None, children) -> html.Div:
    """Standard section wrapper."""
    content = [title_node, children] if title_node is not None else [children]
    return html.Div(content, className="section-container")

def alert_card(alert: dict) -> html.Div:
    """Creates a themed smart alert card for the Intelligence dashboard."""
    level = alert.get("level", "info")
    # Map 'danger' to 'danger', 'warning' to 'warning', 'info' to 'info', 'ok' to 'ok'
    # These match the CSS classes in base.css
    return html.Div([
        html.Span(alert.get("icon", "ℹ"), className="alert-icon"),
        html.Div([
            html.Div(alert.get("title", ""), className="smart-alert-title"),
            html.Div(alert.get("detail", ""), className="smart-alert-detail"),
        ]),
    ], className=f"smart-alert {level}")

def txn_table(history: list[dict]) -> html.Element:
    """Renders the transaction history table with deep-linking to positions."""
    if not history:
        return html.P("No transactions yet.", className="txn-empty")

    rows = [
        html.Tr([
            html.Td(t["date"], className="table-td"),
            html.Td(
                html.A(t["ticker"], href="/positions", className="ticker-link"),
                className="table-td", style={"fontWeight": "500"}
            ),
            html.Td(
                t["type"].upper(),
                className="table-td",
                style={"color": "var(--green)" if t["type"] == "buy" else "var(--red)", "fontWeight": "600"}
            ),
            html.Td(f"{float(t['shares']):g}", className="table-td"),
            html.Td(f"${float(t['price']):,.3f}", className="table-td"),
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
    return html.Div(
        [
            html.Div(dmc.Skeleton(height=10, width="40%", radius="sm"), className="stat-card-label-row"),
            dmc.Skeleton(height=24, width="80%", radius="sm", style={"marginTop": "6px"}),
            dmc.Skeleton(height=10, width="60%", radius="sm", style={"marginTop": "10px"}),
        ],
        className="stat-card-container",
    )

def table_skeleton(rows: int = 5, cols: int = 6) -> html.Div:
    """Pulsing placeholder for a table"""
    return html.Div(
        [
            html.Div(
                [dmc.Skeleton(height=32, radius="sm", style={"marginBottom": "8px"}) for _ in range(rows + 1)],
                style={"padding": "12px"}
            )
        ],
        className="overflow-table",
    )

def chart_skeleton(height: int = 300) -> dmc.Skeleton:
    """Pulsing placeholder for a chart"""
    return dmc.Skeleton(height=height, radius="sm", style={"width": "100%"})