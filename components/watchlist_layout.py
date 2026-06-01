# components/watchlist_layout.py
"""
components/watchlist_layout.py
==============================
Layout for the Watchlist page.
"""

from typing import Any, cast

import dash_mantine_components as dmc
from dash import dcc, html

from components.ui_helpers import (
    chart_skeleton,
    chart_title,
    section,
    stat_card_skeleton,
    table_skeleton,
)


def create_watchlist_layout() -> html.Div:
    """
    Construct the watchlist page layout.
    """
    return html.Div(
        [
            # Hidden input to receive reordered ticker list from Javascript
            dcc.Input(id="watchlist-order-input", type="text", style={"display": "none"}),
            # ── Page Header Row ───────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Market Watchlist", className="header-title"),
                            html.P(
                                "Track potential purchases · Real-time metrics",
                                className="header-subtitle",
                            ),
                        ],
                        className="header-title-row",
                        style={"flex": "0 0 auto"},
                    ),
                ],
                className="page-header-row",
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "16px 24px",
                    "borderBottom": "0.5px solid var(--border)",
                    "marginBottom": "16px",
                },
            ),
            # ── Main Content: Table & Chart ───────────────────────────────────
            section(
                None,
                html.Div(
                    [
                        # Left: Table
                        html.Div(
                            [
                                html.Div(
                                    [
                                        chart_title("Watched Assets"),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        dmc.TextInput(
                                                            id="watchlist-input",
                                                            placeholder="Ticker (e.g. VAS)",
                                                            size="xs",
                                                            style={"width": "120px"},
                                                        ),
                                                        html.Div(
                                                            id="watchlist-ticker-hint",
                                                            style={
                                                                "position": "absolute",
                                                                "top": "100%",
                                                                "left": "0",
                                                                "fontSize": "10px",
                                                                "color": "var(--cyan)",
                                                                "whiteSpace": "nowrap",
                                                                "zIndex": "10",
                                                            },
                                                        ),
                                                    ],
                                                    style={"position": "relative"},
                                                ),
                                                html.Button(
                                                    "Add",
                                                    id="watchlist-add-btn",
                                                    n_clicks=0,
                                                    className="btn-primary btn-sm",
                                                    style={"marginLeft": "8px"},
                                                ),
                                                html.P(
                                                    id="watchlist-msg",
                                                    className="txn-status-msg",
                                                    style={
                                                        "margin": "0 0 0 8px",
                                                        "fontSize": "10px",
                                                    },
                                                ),
                                            ],
                                            style={
                                                "marginLeft": "auto",
                                                "display": "flex",
                                                "alignItems": "center",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "12px",
                                    },
                                ),
                                dcc.Loading(
                                    html.Div(id="watchlist-table-container"),
                                    custom_spinner=table_skeleton(5),
                                ),
                            ],
                            style={"flex": "1.5", "marginRight": "24px"},
                        ),
                        # Right: Chart
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            "Price Performance",
                                            id="watchlist-chart-title",
                                            className="chart-title-text",
                                        ),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "1M",
                                                    id={"type": "wl-period-btn", "index": "1mo"},
                                                    className="btn-sm",
                                                    n_clicks=0,
                                                ),
                                                html.Button(
                                                    "6M",
                                                    id={"type": "wl-period-btn", "index": "6mo"},
                                                    className="btn-sm",
                                                    n_clicks=0,
                                                ),
                                                html.Button(
                                                    "1Y",
                                                    id={"type": "wl-period-btn", "index": "1y"},
                                                    className="btn-sm",
                                                    n_clicks=0,
                                                ),
                                                html.Button(
                                                    "5Y",
                                                    id={"type": "wl-period-btn", "index": "5y"},
                                                    className="btn-sm",
                                                    n_clicks=0,
                                                ),
                                                html.Button(
                                                    "Max",
                                                    id={"type": "wl-period-btn", "index": "max"},
                                                    className="btn-sm",
                                                    n_clicks=0,
                                                ),
                                            ],
                                            id="wl-period-btn-row",
                                            style={
                                                "display": "flex",
                                                "gap": "6px",
                                                "marginLeft": "auto",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "marginBottom": "12px",
                                    },
                                ),
                                html.Div(
                                    id="watchlist-chart-container",
                                    children=dcc.Graph(
                                        id="watchlist-chart",
                                        config=cast(Any, {"displayModeBar": False}),
                                    ),
                                ),
                                dcc.Loading(
                                    html.Div(
                                        id="watchlist-stat-cards",
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "repeat(4, 1fr)",
                                            "gap": "8px",
                                            "marginTop": "14px",
                                        },
                                    ),
                                    custom_spinner=html.Div(
                                        [stat_card_skeleton() for _ in range(4)],
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "repeat(4, 1fr)",
                                            "gap": "8px",
                                            "marginTop": "14px",
                                        },
                                    ),
                                ),
                                dcc.Loading(
                                    html.Div(id="watchlist-tech-signals-container"),
                                    custom_spinner=html.Div(
                                        className="skeleton",
                                        style={
                                            "height": "30px",
                                            "width": "300px",
                                            "margin": "12px 0",
                                            "borderRadius": "4px",
                                        },
                                    ),
                                ),
                                dcc.Loading(
                                    html.Div(id="watchlist-ai-insight-container"),
                                    custom_spinner=html.Div(
                                        className="skeleton",
                                        style={
                                            "height": "100px",
                                            "width": "100%",
                                            "marginTop": "10px",
                                            "borderRadius": "8px",
                                        },
                                    ),
                                ),
                                html.Div(
                                    [
                                        html.P(
                                            "Research notes",
                                            style={
                                                "fontSize": "10px",
                                                "fontWeight": "600",
                                                "color": "var(--t-sec)",
                                                "textTransform": "uppercase",
                                                "letterSpacing": "0.5px",
                                                "margin": "14px 0 6px",
                                            },
                                        ),
                                        dmc.Textarea(
                                            id="watchlist-notes-input",
                                            placeholder="Add your research notes for this ticker...",
                                            minRows=3,
                                            style={"width": "100%", "fontSize": "12px"},
                                        ),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Save Note",
                                                    id="watchlist-notes-save-btn",
                                                    n_clicks=0,
                                                    className="btn-sm btn-primary",
                                                    style={"marginTop": "8px"},
                                                ),
                                                html.Span(
                                                    id="watchlist-notes-msg",
                                                    style={
                                                        "fontSize": "11px",
                                                        "color": "var(--t-sec)",
                                                        "marginLeft": "10px",
                                                    },
                                                ),
                                            ],
                                            style={"display": "flex", "alignItems": "center"},
                                        ),
                                    ],
                                    style={"marginTop": "4px"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                    ],
                    style={"display": "flex", "width": "100%"},
                ),
            ),
        ],
        className="page-root",
    )
