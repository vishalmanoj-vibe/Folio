"""
pages/intelligence.py
======================
Portfolio Intelligence page.
Route: /intelligence
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, register_page

from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC
)
from components.ui_helpers import section, chart_title

register_page(__name__, path="/intelligence", title="Portfolio Intelligence")


# ─────────────────────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────────────────────

def layout() -> html.Div:
    return html.Div(
        [
            # ── Nav header ────────────────────────────────────────────────────
            html.Div(
                [
                    html.A("← Portfolio", href="/", className="back-link"),
                    html.Span("Portfolio Intelligence", className="page-title", style={"marginLeft": "16px"}),
                    html.Span("Risk · Allocation · Smart alerts", className="page-subtitle", style={"marginLeft": "10px", "flex": "1"}),
                    html.Button("Refresh now", id="refresh-btn", n_clicks=0, className="btn-sm"),
                ],
                className="page-header-row",
            ),

            # ── Data source note ──────────────────────────────────────────────
            html.Div(
                id="intel-data-note",
                className="intel-data-note",
            ),

            # ── A. Risk scorecard ─────────────────────────────────────────────────────
            section(
                chart_title(
                    "Risk metrics",
                    "Key risk stats calculated from the price history window. "
                    "Hover each card for an explanation of what the number means.",
                ),
                html.Div(
                    id="intel-risk-cards",
                    className="metrics-row",
                ),
            ),

            # ── B. Equity curve ───────────────────────────────────────────────
            section(
                chart_title(
                    "Cumulative return",
                    "Shows how $1 invested across your portfolio has grown over time. "
                    "Each ETF is weighted by its share of your total holdings. "
                    "The line starts at 0% on the first day all holdings have data.",
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-equity-chart",
                               config={"displayModeBar": False}),
                    type="circle", color=COLORS[0],
                ),
            ),

            # ── C. Drawdown curve ─────────────────────────────────────────────
            section(
                chart_title(
                    "Drawdown",
                    "How far your portfolio has fallen from its peak at any point in time. "
                    "A reading of -10% means you are 10% below the highest value reached. "
                    "The lowest point (max drawdown) is marked on the chart.",
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-drawdown-chart",
                               config={"displayModeBar": False}),
                    type="circle", color=RED,
                ),
            ),

            # ── D · E · F  three-column bar charts ───────────────────────────
            html.Div(
                [
                    # D — Volatility per ETF
                    html.Div(
                        [
                            chart_title(
                                "Volatility by ETF",
                                "Annualised price volatility for each ETF over the loaded period. "
                                "Lower is steadier. Green = below 12%, amber = 12–20%, red = above 20%.",
                            ),
                            dcc.Loading(
                                # No style= height — Plotly controls canvas size
                                dcc.Graph(id="intel-vol-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[2],
                            ),
                        ],
                        className="chart-col-min-260",
                    ),

                    # E — Sector exposure
                    html.Div(
                        [
                            chart_title(
                                "Sector exposure",
                                "Your portfolio's blend across market sectors, weighted by holding value. "
                                "A single sector above 40% signals concentration risk. "
                                "Data is sourced from Yahoo Finance and cached for 24 hours.",
                            ),
                            dcc.Loading(
                                dcc.Graph(id="intel-sector-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[3],
                            ),
                        ],
                        className="chart-col-min-260",
                    ),

                    # F — Geographic exposure
                    html.Div(
                        [
                            chart_title(
                                "Geographic exposure",
                                "Where your money is invested in the world, weighted by holding value. "
                                "Region is inferred from each ETF's top holdings by their stock exchange. "
                                "Data is cached for 24 hours.",
                            ),
                            dcc.Loading(
                                dcc.Graph(id="intel-geo-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[4],
                            ),
                        ],
                        className="chart-col-min-260",
                    ),
                ],
                className="section-container three-col-layout",
                style={"padding": "20px 24px"},
            ),

            # ── G. Smart alerts ───────────────────────────────────────────────
            html.Div(
                [
                    chart_title(
                        "Smart alerts",
                        "Rule-based insights from holdings, allocation weights, "
                        "and risk metrics.",
                    ),
                    html.Div(
                        id="intel-alerts",
                        className="flex-col-container",
                    ),
                ],
            ),

            # ── H. Detail Modal ───────────────────────────────────────────────
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="intel-modal-title")),
                    dbc.ModalBody(
                        dcc.Loading(
                            dcc.Graph(id="intel-modal-graph", config={"displayModeBar": False}),
                            type="circle", color=COLORS[0],
                        )
                    ),
                    dbc.ModalFooter(
                        html.Button("Close", id="intel-modal-close-btn", className="btn-md", n_clicks=0)
                    ),
                ],
                id="intel-detail-modal",
                is_open=False,
                size="lg",
                centered=True,
            ),
        ],
        className="page-root",
    )