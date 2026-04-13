from dash import html
from config import (
    SURFACE, BORDER, T_PRI, T_SEC, GREEN, RED, CHART_INFO
)


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str = T_PRI,
    sub_color: str = T_SEC,
) -> html.Div:
    return html.Div(
        [
            html.P(label, style={"fontSize": "12px", "color": T_SEC, "margin": "0 0 4px"}),
            html.P(value, style={"fontSize": "20px", "fontWeight": "500", "margin": "0", "color": color}),
            html.P(sub,   style={"fontSize": "11px", "color": sub_color, "margin": "3px 0 0"}) if sub else None,
        ],
        style={
            "background":    SURFACE,
            "borderRadius":  "10px",
            "padding":       "14px 18px",
            "flex":          "1",
            "minWidth":      "130px",
        },
    )


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Chart section title with an optional hoverable (i) info badge."""
    tip = CHART_INFO.get(info_key, ("", ""))[1] if info_key else ""
    children = [
        html.Span(label, style={"fontSize": "13px", "fontWeight": "500", "color": T_PRI})
    ]
    if tip:
        children.append(
            html.Span("i", title=tip, style={
                "display":        "inline-flex",
                "alignItems":     "center",
                "justifyContent": "center",
                "width":          "16px",
                "height":         "16px",
                "borderRadius":   "50%",
                "background":     SURFACE,
                "border":         f"1px solid {BORDER}",
                "fontSize":       "10px",
                "color":          T_SEC,
                "cursor":         "help",
                "marginLeft":     "6px",
                "fontWeight":     "500",
            })
        )
    return html.Div(
        children,
        style={"display": "inline-flex", "alignItems": "center", "marginBottom": "6px"},
    )


def section(title_node: html.Div, children) -> html.Div:
    return html.Div(
        [title_node, children],
        style={"padding": "16px 24px", "borderBottom": f"0.5px solid {BORDER}"},
    )


def txn_table(history: list[dict]) -> html.Element:
    """Render the transaction log as an HTML table."""
    if not history:
        return html.P("No transactions yet.", style={"color": T_SEC, "fontSize": "13px"})

    th_s = {
        "fontSize": "11px", "color": T_SEC, "fontWeight": "500",
        "padding": "6px 10px", "borderBottom": f"1px solid {BORDER}",
        "backgroundColor": SURFACE, "textAlign": "left", "whiteSpace": "nowrap",
    }
    td_s = {
        "fontSize": "12px", "padding": "6px 10px",
        "borderBottom": f"0.5px solid {BORDER}", "whiteSpace": "nowrap",
    }

    rows = [
        html.Tr([
            html.Td(t["date"],   style=td_s),
            html.Td(t["ticker"], style={**td_s, "fontWeight": "500"}),
            html.Td(
                t["type"].upper(),
                style={**td_s, "color": GREEN if t["type"] == "buy" else RED, "fontWeight": "500"},
            ),
            html.Td(str(t["shares"]),                                style=td_s),
            html.Td(f"${float(t['price']):,.4f}",                    style=td_s),
            html.Td(f"${float(t['shares']) * float(t['price']):,.2f}", style=td_s),
        ])
        for t in reversed(history)
    ]

    return html.Table(
        [
            html.Thead(html.Tr([
                html.Th(c, style=th_s)
                for c in ["Date", "Ticker", "Type", "Shares", "Price", "Total"]
            ])),
            html.Tbody(rows),
        ],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
