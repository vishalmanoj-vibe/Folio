"""
components/ui_helpers.py
=========================
Refined UI helpers. Keeps the original clean aesthetic you prefer, with small polish:
- Better spacing and typography on stat cards
- Improved transaction history table (clickable tickers, better alignment)
- Cleaner chart titles
"""

from dash import html
from config.constants import GREEN, RED, CHART_INFO


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = "var(--t-pri)",
    sub_color: str = "var(--t-sec)",
) -> html.Div:
    """Original style stat card with subtle improvements in spacing and weight"""
    return html.Div(
        [
            html.P(
                label,
                style={
                    "fontSize": "12.5px",
                    "color": "var(--t-sec)",
                    "margin": "0 0 6px",
                    "fontWeight": "400"
                }
            ),
            html.P(
                value,
                style={
                    "fontSize": "24px",
                    "fontWeight": "600",
                    "margin": "0",
                    "color": color,
                    "letterSpacing": "-0.02em"
                }
            ),
            html.P(
                sub,
                style={
                    "fontSize": "11.5px",
                    "color": sub_color,
                    "margin": "5px 0 0"
                }
            ) if sub else None,
        ],
        style={
            "background": "var(--surface)",
            "borderRadius": "10px",
            "padding": "16px 18px",
            "flex": "1",
            "minWidth": "160px",
            "border": "1px solid var(--border)",
        },
    )


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Clean chart title with improved info icon"""
    tip = CHART_INFO.get(info_key, ("", ""))[1] if info_key else ""
    
    children = [
        html.Span(
            label,
            style={"fontSize": "13.5px", "fontWeight": "600", "color": "var(--t-pri)"}
        )
    ]
    
    if tip:
        children.append(
            html.Span(
                "ℹ",
                title=tip,
                style={
                    "display": "inline-flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "width": "17px",
                    "height": "17px",
                    "borderRadius": "50%",
                    "background": "var(--surface)",
                    "border": "1px solid var(--border)",
                    "fontSize": "10.5px",
                    "color": "var(--t-sec)",
                    "cursor": "help",
                    "marginLeft": "7px",
                }
            )
        )
    
    return html.Div(
        children,
        style={"display": "inline-flex", "alignItems": "center", "marginBottom": "9px"}
    )


def section(title_node: html.Div, children) -> html.Div:
    """Original section style"""
    return html.Div(
        [title_node, children],
        style={
            "padding": "20px 24px",
            "borderBottom": "0.5px solid var(--border)"
        },
    )


def txn_table(history: list[dict]) -> html.Element:
    """Polished transaction table - same style as original but better readability"""
    if not history:
        return html.P(
            "No transactions yet.",
            style={"color": "var(--t-sec)", "fontSize": "13px", "padding": "12px 0"}
        )

    th_s = {
        "fontSize": "11.5px",
        "color": "var(--t-sec)",
        "fontWeight": "600",
        "padding": "10px 12px",
        "borderBottom": "1px solid var(--border)",
        "textAlign": "left",
        "whiteSpace": "nowrap",
    }

    td_s = {
        "fontSize": "13px",
        "padding": "10px 12px",
        "borderBottom": "0.5px solid var(--border)",
        "whiteSpace": "nowrap",
        "color": "var(--t-pri)",
    }

    rows = [
        html.Tr([
            html.Td(t["date"], style=td_s),
            html.Td(
                html.A(
                    t["ticker"], 
                    href=f"/etf/{t['ticker']}", 
                    className="ticker-link"
                ),
                style={**td_s, "fontWeight": "500"}
            ),
            html.Td(
                t["type"].upper(),
                style={
                    **td_s,
                    "color": GREEN if t["type"] == "buy" else RED,
                    "fontWeight": "600"
                }
            ),
            html.Td(f"{float(t['shares']):,.2f}", style=td_s),
            html.Td(f"${float(t['price']):,.4f}", style=td_s),
            html.Td(f"${float(t['shares']) * float(t['price']):,.2f}", style=td_s),
        ])
        for t in reversed(history)
    ]

    return html.Table(
        [
            html.Thead(html.Tr([html.Th(c, style=th_s) for c in ["Date", "Ticker", "Type", "Shares", "Price", "Total"]])),
            html.Tbody(rows),
        ],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "background": "var(--surface)",
            "borderRadius": "8px",
            "overflow": "hidden",
        },
    )