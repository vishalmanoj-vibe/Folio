# pages/positions.py
"""
pages/positions.py
==================
Positions overview page — card grid and detailed ETF breakdown.
Route: /positions
"""

from typing import Any, cast

import dash
import dash_mantine_components as dmc
from dash import dcc, html

from components.ui_helpers import (
    chart_skeleton,
    chart_title,
    section,
    stat_card_skeleton,
    table_skeleton,
)

dash.register_page(__name__, path="/positions", title="Positions")


def layout(**kwargs) -> html.Div:
    return html.Div(
        [
            # ── Page Header ──────────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Positions", className="header-title"),
                            html.P("Detailed view per ETF holding", className="header-subtitle"),
                        ],
                        className="header-title-row",
                    ),
                ],
                className="page-header-row",
                style={"display": "flex", "alignItems": "center"},
            ),
            html.Div(
                [
                    # ── Holding Cards Grid ──────────────────────────────────────────
                    section(
                        None, html.Div(id="positions-card-grid", className="holding-card-grid")
                    ),
                    # ── ETF Detail Panel ────────────────────────────────────────────
                    # The section remains visible, but children are populated by callbacks.
                    # Titles are moved into children to prevent empty headers on load.
                    section(
                        html.Div(id="positions-detail-title"),
                        html.Div(
                            [
                                dcc.Loading(
                                    html.Div(id="etf-detail-cards", className="etf-detail-grid"),
                                    custom_spinner=html.Div(
                                        [stat_card_skeleton() for _ in range(6)],
                                        className="etf-detail-grid",
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "repeat(6, 1fr)",
                                            "gap": "8px",
                                            "width": "100%",
                                        },
                                    ),
                                ),
                                dcc.Loading(
                                    html.Div(id="positions-tech-signals-container"),
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
                                    html.Div(id="ai-insight-container"),
                                    custom_spinner=html.Div(
                                        className="skeleton",
                                        style={
                                            "height": "120px",
                                            "width": "100%",
                                            "marginTop": "10px",
                                            "marginBottom": "24px",
                                            "borderRadius": "8px",
                                        },
                                    ),
                                ),
                                # Price Chart Section (Dynamic)
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                chart_title("Price history", "positions-price"),
                                                html.Div(
                                                    id="positions-period-btns",
                                                    className="flex-row-gap",
                                                    style={"marginLeft": "auto"},
                                                ),
                                            ],
                                            id="positions-price-chart-header",
                                            className="flex-row flex-center",
                                            style={"marginBottom": "12px", "display": "none"},
                                        ),
                                        html.Div(
                                            dcc.Graph(
                                                id="positions-price-chart",
                                                config=cast(Any, {"displayModeBar": False}),
                                                style={"height": "350px"},
                                            ),
                                            id="positions-price-chart-container",
                                        ),
                                    ],
                                    style={"marginTop": "24px"},
                                ),
                                # Ticker-Specific Dividend History (Dynamic)
                                dcc.Loading(
                                    html.Div(id="positions-ticker-dividend-container"),
                                    custom_spinner=html.Div(
                                        className="skeleton",
                                        style={
                                            "height": "180px",
                                            "width": "100%",
                                            "marginTop": "24px",
                                            "borderRadius": "8px",
                                        },
                                    ),
                                ),
                                # Transaction Table (Dynamic)
                                dcc.Loading(
                                    html.Div(id="positions-txn-table-container"),
                                    custom_spinner=table_skeleton(3),
                                ),
                            ],
                            id="etf-detail-panel",
                        ),
                    ),
                    # ── Portfolio Dividend Insights (Global) ─────────────────────────
                    section(
                        None,
                        html.Details(
                            [
                                html.Summary(
                                    "Portfolio Dividend Insights", className="txn-history-summary"
                                ),
                                html.Div(
                                    [
                                        # Bar chart for past year payouts
                                        dcc.Loading(
                                            html.Div(
                                                id="positions-portfolio-dividend-chart-container"
                                            ),
                                            custom_spinner=html.Div(
                                                className="skeleton",
                                                style={
                                                    "height": "200px",
                                                    "width": "100%",
                                                    "marginBottom": "24px",
                                                    "borderRadius": "8px",
                                                },
                                            ),
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        chart_title("Annual estimated income"),
                                                        html.Div(
                                                            id="positions-dividend-income-chart",
                                                            className="dividend-progress-container",
                                                        ),
                                                    ],
                                                    className="grid-item-1",
                                                ),
                                                html.Div(
                                                    [
                                                        chart_title("Yield comparison (%)"),
                                                        html.Div(
                                                            id="positions-dividend-yield-chart",
                                                            className="dividend-progress-container",
                                                        ),
                                                    ],
                                                    className="grid-item-1",
                                                ),
                                            ],
                                            className="charts-grid-row",
                                            style={"marginTop": "20px"},
                                        ),
                                        html.Div(
                                            [
                                                chart_title("Recent global distributions"),
                                                html.Div(
                                                    id="positions-dividend-table",
                                                    className="overflow-table",
                                                    style={"marginTop": "10px"},
                                                ),
                                            ],
                                            style={"marginTop": "24px"},
                                        ),
                                    ],
                                    id="positions-dividend-insights-container",
                                ),
                            ],
                            id="positions-dividend-details",
                        ),
                    ),
                ]
            ),
        ],
        className="page-root",
    )
