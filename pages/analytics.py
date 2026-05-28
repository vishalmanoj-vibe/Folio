# pages/analytics.py
"""
pages/analytics.py
==================
Deep-dive charts and secondary metrics.
Route: /analytics
"""

import dash
import dash_mantine_components as dmc
from dash import dcc, html

from components.ui_helpers import chart_skeleton, chart_title, section
from config.constants import COLORS

dash.register_page(__name__, path="/analytics", title="Deep Dive")


def layout():
    return html.Div(
        [
            # ── Page Header Row ───────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Deep Dive", className="header-title"),
                            html.P(
                                "Allocation, risk & performance analysis",
                                className="header-subtitle",
                            ),
                        ],
                        className="header-title-row",
                    ),
                    html.Div([], className="header-controls"),
                ],
                className="page-header-row",
            ),
            # ── Configure Holdings Sources — top-level collapse ──
            dmc.Collapse(
                html.Div(
                    [
                        html.Div(
                            [
                                # Existing URL table
                                html.Div(id="holdings-url-table", style={"marginBottom": "16px"}),
                                # Add new URL form
                                html.Div(
                                    [
                                        dmc.TextInput(
                                            id="holdings-url-ticker-input",
                                            placeholder="Ticker (e.g. VHY)",
                                            style={"width": "130px", "flexShrink": "0"},
                                            size="sm",
                                        ),
                                        dmc.TextInput(
                                            id="holdings-url-input",
                                            placeholder="Paste fund page URL (e.g. https://www.vanguard.com.au/...)",
                                            style={"flex": "1"},
                                            size="sm",
                                        ),
                                        dmc.Button(
                                            "Save URL",
                                            id="holdings-url-save-btn",
                                            size="sm",
                                            variant="filled",
                                            color="teal",
                                            style={"flexShrink": "0"},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "gap": "10px",
                                        "alignItems": "center",
                                    },
                                ),
                                html.Div(
                                    id="holdings-url-save-status",
                                    style={
                                        "fontSize": "12px",
                                        "marginTop": "8px",
                                        "color": "var(--t-muted)",
                                    },
                                ),
                            ],
                            style={
                                "padding": "20px 24px",
                                "background": "var(--surface)",
                                "borderBottom": "1px solid var(--border)",
                                "marginBottom": "20px",
                                "borderRadius": "8px",
                            },
                        ),
                    ]
                ),
                id="holdings-url-collapse",
                opened=False,
                transitionDuration=200,
            ),
            # ── Tabs Navigation ───────────────────────────────────────────────
            dmc.Tabs(
                [
                    # TabsList row — tabs on the left, configure button on the right
                    dmc.TabsList(
                        [
                            dmc.TabsTab("Allocation", value="allocation"),
                            dmc.TabsTab("ETF Holdings", value="holdings"),
                            dmc.TabsTab("Risk & Performance", value="performance"),
                            # Spacer pushes the configure button to the far right
                            html.Div(style={"flex": "1"}),
                            html.Div(
                                [
                                    html.Span(
                                        "⚙", style={"marginRight": "6px", "fontSize": "13px"}
                                    ),
                                    html.Span(
                                        "Configure Sources",
                                        style={"fontSize": "12px", "fontWeight": "600"},
                                    ),
                                ],
                                id="holdings-url-toggle",
                                n_clicks=0,
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "cursor": "pointer",
                                    "padding": "6px 12px",
                                    "borderRadius": "6px",
                                    "color": "var(--t-sec)",
                                    "border": "1px solid var(--border)",
                                    "marginBottom": "4px",
                                    "userSelect": "none",
                                    "transition": "background 150ms",
                                    "whiteSpace": "nowrap",
                                },
                            ),
                        ],
                        grow=True,
                        className="tabs-list-custom",
                    ),
                    # ── Tab 1: Allocation ─────────────────────────────────────────
                    dmc.TabsPanel(
                        html.Div(
                            [
                                # Treemap with Hierarchy Toggle
                                section(
                                    html.Div(
                                        [
                                            chart_title(
                                                "Portfolio Allocation Breakdown", "treemap-desc"
                                            ),
                                            html.Div(style={"flex": "1"}),
                                            dmc.SegmentedControl(
                                                id="treemap-mode",
                                                data=[
                                                    {"label": "Flat Tickers", "value": "flat"},
                                                    {"label": "By Sector", "value": "sector"},
                                                    {"label": "By Region", "value": "geo"},
                                                ],
                                                value="sector",
                                                size="xs",
                                                radius="xl",
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "marginBottom": "20px",
                                        },
                                    ),
                                    html.Div(
                                        [
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="portfolio-treemap",
                                                    config={
                                                        "displayModeBar": False,
                                                        "doubleClick": "reset",
                                                    },
                                                    style={"height": "600px"},
                                                    className="treemap-canvas",
                                                ),
                                                custom_spinner=chart_skeleton(600),
                                            ),
                                            html.Div(
                                                "Colour encodes allocation concentration. Size encodes market value.",
                                                style={
                                                    "fontSize": "11px",
                                                    "color": "var(--t-muted)",
                                                    "marginTop": "12px",
                                                    "textAlign": "center",
                                                },
                                            ),
                                        ]
                                    ),
                                ),
                            ]
                        ),
                        value="allocation",
                    ),
                    # ── Tab 2: ETF Holdings ───────────────────────────────────────
                    dmc.TabsPanel(
                        html.Div(
                            [
                                section(
                                    html.Div(
                                        [
                                            chart_title("ETF Holdings Exposure", "holdings-desc"),
                                            html.Div(
                                                id="holdings-freshness-note",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "var(--t-muted)",
                                                },
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "center",
                                            "marginBottom": "20px",
                                        },
                                    ),
                                    html.Div(
                                        [
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="holdings-bubble-chart",
                                                    config={"displayModeBar": False},
                                                    style={"height": "600px"},
                                                ),
                                                custom_spinner=chart_skeleton(600),
                                            ),
                                            html.Div(
                                                "Bubble size represents the blended portfolio exposure to each underlying company.",
                                                style={
                                                    "fontSize": "11px",
                                                    "color": "var(--t-muted)",
                                                    "marginTop": "12px",
                                                    "textAlign": "center",
                                                },
                                            ),
                                        ]
                                    ),
                                ),
                            ]
                        ),
                        value="holdings",
                    ),
                    # ── Tab 3: Performance & Risk ─────────────────────────────────
                    dmc.TabsPanel(
                        html.Div(
                            [
                                # Price History
                                section(
                                    html.Div(
                                        [
                                            chart_title(
                                                "Price History — Normalised to 100",
                                                "price-chart-desc",
                                            ),
                                            dmc.SegmentedControl(
                                                id="analytics-period-picker",
                                                data=[
                                                    {"label": "Since purchase", "value": "max"},
                                                    {"label": "1M", "value": "1mo"},
                                                    {"label": "3M", "value": "3mo"},
                                                    {"label": "6M", "value": "6mo"},
                                                    {"label": "1Y", "value": "1y"},
                                                ],
                                                value="1mo",
                                                size="sm",
                                                radius="lg",
                                                className="period-segmented-control",
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "marginBottom": "10px",
                                        },
                                    ),
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="price-chart",
                                            config={"displayModeBar": False},
                                            style={"height": "400px"},
                                        ),
                                        custom_spinner=chart_skeleton(400),
                                    ),
                                ),
                                # Row for Correlation & Volatility
                                section(
                                    None,
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    chart_title(
                                                        "Return Correlation Matrix", "corr-desc"
                                                    ),
                                                    dcc.Loading(
                                                        dcc.Graph(
                                                            id="corr-chart",
                                                            config={"displayModeBar": False},
                                                        ),
                                                        custom_spinner=chart_skeleton(300),
                                                    ),
                                                ],
                                                className="grid-item-1",
                                            ),
                                            html.Div(
                                                [
                                                    chart_title("Volatility by ETF", "vol-desc"),
                                                    dcc.Loading(
                                                        html.Div(
                                                            id="analytics-vol-chart",
                                                            className="dividend-progress-container",
                                                        ),
                                                        custom_spinner=html.Div(
                                                            [
                                                                html.Div(
                                                                    className="skeleton",
                                                                    style={
                                                                        "height": "20px",
                                                                        "width": "100%",
                                                                        "marginBottom": "8px",
                                                                    },
                                                                )
                                                                for _ in range(5)
                                                            ]
                                                        ),
                                                    ),
                                                ],
                                                className="grid-item-1",
                                            ),
                                        ],
                                        className="charts-grid-row",
                                    ),
                                ),
                            ]
                        ),
                        value="performance",
                    ),
                ],
                value="allocation",
                variant="default",
                className="analytics-tabs",
            ),
        ],
        className="page-root",
    )
