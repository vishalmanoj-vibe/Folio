from dash import html
from config import GREEN, RED, CHART_INFO


def stat_card(
    label: str,
    value: str,
    sub: str | None = None,
    color: str | None = None,
    sub_color: str | None = None,
) -> html.Div:
    """
    Premium stat card with subtle hover, spacing, and typography improvements.
    Theme-aware via CSS variables.
    """

    return html.Div(
        [
            html.Div(
                [
                    html.P(
                        label,
                        style={
                            "fontSize": "11px",
                            "color": "var(--t-sec)",
                            "margin": "0",
                            "letterSpacing": "0.3px",
                        },
                    ),
                    html.P(
                        value,
                        style={
                            "fontSize": "20px",
                            "fontWeight": "600",
                            "margin": "2px 0 0",
                            "color": color if color else "var(--t-pri)",
                        },
                    ),
                    html.P(
                        sub,
                        style={
                            "fontSize": "11px",
                            "margin": "4px 0 0",
                            "color": sub_color if sub_color else "var(--t-sec)",
                        },
                    ) if sub else None,
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "2px",
                },
            )
        ],
        style={
            "background":   "var(--surface)",
            "border":       "1px solid var(--border)",
            "borderRadius": "12px",
            "padding":      "14px 16px",
            "flex":         "1",
            "minWidth":     "140px",

            # ✨ NEW (premium feel)
            "boxShadow":    "0 1px 2px rgba(0,0,0,0.05)",
            "transition":   "all 0.18s ease",
        },

        # ✨ Hover effect (Dash supports this)
        **{
            "data-hover": "true"
        }
    )


def chart_title(label: str, info_key: str = "") -> html.Div:
    """Chart section title with improved spacing + cleaner info badge."""
    tip = CHART_INFO.get(info_key, ("", ""))[1] if info_key else ""

    children = [
        html.Span(
            label,
            style={
                "fontSize": "13px",
                "fontWeight": "600",
                "color": "var(--t-pri)",
            },
        )
    ]

    if tip:
        children.append(
            html.Span(
                "i",
                title=tip,
                style={
                    "display":        "inline-flex",
                    "alignItems":     "center",
                    "justifyContent": "center",
                    "width":          "16px",
                    "height":         "16px",
                    "borderRadius":   "50%",
                    "background":     "var(--surface)",
                    "border":         "1px solid var(--border)",
                    "fontSize":       "10px",
                    "color":          "var(--t-sec)",
                    "cursor":         "help",
                    "marginLeft":     "6px",
                    "fontWeight":     "500",
                },
            )
        )

    return html.Div(
        children,
        style={
            "display": "flex",
            "alignItems": "center",
            "marginBottom": "8px",
        },
    )


def section(title_node: html.Div, children) -> html.Div:
    return html.Div(
        [title_node, children],
        style={
            "padding":      "18px 24px",
            "borderBottom": "0.5px solid var(--border)",
        },
    )


def txn_table(history: list[dict]) -> html.Element:
    """Styled transaction log with improved spacing and readability."""

    if not history:
        return html.P(
            "No transactions yet.",
            style={"color": "var(--t-sec)", "fontSize": "13px"}
        )

    th_s = {
        "fontSize":       "11px",
        "color":          "var(--t-sec)",
        "fontWeight":     "500",
        "padding":        "8px 12px",
        "borderBottom":   "1px solid var(--border)",
        "backgroundColor":"var(--surface)",
        "textAlign":      "left",
        "whiteSpace":     "nowrap",
    }

    td_s = {
        "fontSize":    "12px",
        "padding":     "8px 12px",
        "borderBottom":"0.5px solid var(--border)",
        "whiteSpace":  "nowrap",
        "color":       "var(--t-pri)",
    }

    rows = [
        html.Tr(
            [
                html.Td(t["date"],   style=td_s),
                html.Td(t["ticker"], style={**td_s, "fontWeight": "500"}),
                html.Td(
                    t["type"].upper(),
                    style={
                        **td_s,
                        "color": GREEN if t["type"] == "buy" else RED,
                        "fontWeight": "500",
                    },
                ),
                html.Td(str(t["shares"]), style=td_s),
                html.Td(f"${float(t['price']):,.4f}", style=td_s),
                html.Td(f"${float(t['shares']) * float(t['price']):,.2f}", style=td_s),
            ]
        )
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
        style={
            "width": "100%",
            "borderCollapse": "collapse",
        },
    )