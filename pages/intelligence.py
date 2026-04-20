"""
pages/intelligence.py
======================
Portfolio Intelligence page.
Route: /intelligence
"""

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html, register_page

from config.constants import COLORS, RED
from components.ui_helpers import section, chart_title

from components.header import create_header

register_page(__name__, path="/intelligence", title="Portfolio Intelligence")

def layout() -> html.Div:
    return html.Div(
        [
            # ── Nav header ────────────────────────────────────────────────────
            create_header(
                title="Portfolio Intelligence",
                subtitle="Deep insights into your ETF holdings",
                links_before=[
                    {"label": "Overview", "href": "/"},
                    {"label": "Analytics", "href": "/analytics"}
                ],
                show_pdf=False,
                market_status=html.Div(id="market-status")
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
                html.Div(
                    [
                        chart_title(
                            "Cumulative return",
                            "Shows how $1 invested across your portfolio has grown over time. "
                            "Each ETF is weighted by its share of your total holdings. "
                            "The line starts at 0% on the first day all holdings have data.",
                        ),
                        html.Div(
                            [
                                # Prediction Controls
                                html.Div([
                                    html.Span("Show Prediction", style={"marginRight": "10px", "fontSize": "13px", "color": "var(--t-sec)"}),
                                    dbc.Switch(
                                        id="intel-pred-toggle",
                                        value=False,
                                        className="custom-switch",
                                        style={"display": "inline-block", "marginRight": "16px"}
                                    ),
                                ], style={"display": "flex", "alignItems": "center", "marginRight": "12px"}),
                                
                                dmc.Select(
                                    id="intel-period-picker",
                                    data=[
                                        {"label": "Since purchase", "value": "max"},
                                        {"label": "1 month",        "value": "1mo"},
                                        {"label": "3 months",       "value": "3mo"},
                                        {"label": "6 months",       "value": "6mo"},
                                        {"label": "1 year",         "value": "1y"},
                                        {"label": "2 years",        "value": "2y"},
                                        {"label": "5 years",        "value": "5y"},
                                    ],
                                    value="3mo",
                                    allowDeselect=False,
                                    persistence=True,
                                    style={"width": "140px"},
                                ),
                            ], 
                            style={"display": "flex", "alignItems": "center", "marginLeft": "auto"}
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-equity-chart", config={"displayModeBar": False}),
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
        ],
        className="page-root",
    )