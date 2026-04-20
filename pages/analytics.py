"""
pages/analytics.py
==================
Deep-dive charts and secondary metrics.
Route: /analytics
"""

import dash
from dash import html, dcc
from components.header import create_header
from components.ui_helpers import chart_title

dash.register_page(__name__, path="/analytics", title="Portfolio — Analytics")

def layout():
    return html.Div([
        # ── Header ────────────────────────────────────────────────────────
        create_header(
            title="Portfolio Analytics",
            subtitle="Secondary performance metrics & allocation breakdown",
            links_before=[
                {"label": "Overview", "href": "/"}
            ],
            links_after=[
                {"label": "Intelligence", "href": "/intelligence"}
            ],
            show_pdf=True,
            market_status=html.Div(id="market-status")
        ),
        # ── Filters Row ───────────────────────────────────────────────────
        html.Div(
            [
                html.Div(
                    [
                        dcc.Dropdown(
                            id="analytics-period-picker",
                            options=[
                                {"label": "Since purchase", "value": "max"},
                                {"label": "1 month",        "value": "1mo"},
                                {"label": "3 months",       "value": "3mo"},
                                {"label": "6 months",       "value": "6mo"},
                                {"label": "1 year",         "value": "1y"},
                                {"label": "2 years",        "value": "2y"},
                            ],
                            value="3mo", clearable=False, searchable=False,
                            persistence=True, persistence_type="session",
                            style={"width": "130px", "fontSize": "12px"},
                        ),
                        dcc.Dropdown(
                            id="analytics-pnl-mode",
                            options=[
                                {"label": "Dollar ($)",     "value": "dollar"},
                                {"label": "Percentage (%)", "value": "pct"},
                            ],
                            value="dollar", clearable=False, searchable=False,
                            persistence=True, persistence_type="session",
                            style={"width": "130px", "fontSize": "12px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "12px"}
                ),
            ],
            style={
                "display": "flex", "alignItems": "center", "justifyContent": "flex-end",
                "padding": "12px 24px", "gap": "12px",
                "borderBottom": "0.5px solid var(--border)"
            }
        ),

        # ── Charts Grid ───────────────────────────────────────────────────
        html.Div([
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Price history — normalised to 100", "price-chart"),
                                 dcc.Graph(id="price-chart", config={"displayModeBar": False})],
                                 className="grid-item-2",
                            ),
                            html.Div(
                                [chart_title("Portfolio allocation", "allocation"),
                                 dcc.Graph(id="allocation-chart", config={"displayModeBar": False})],
                                 className="grid-item-1",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 dcc.Graph(id="pnl-bar-chart", config={"displayModeBar": False})],
                                 className="grid-item-1-half",
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 dcc.Graph(id="day-pnl-chart", config={"displayModeBar": False})],
                                 className="grid-item-1-half",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 dcc.Graph(id="dividend-chart", config={"displayModeBar": False})],
                                 className="grid-item-1-half",
                            ),
                            html.Div(
                                [chart_title("Return correlation matrix", "correlation"),
                                 dcc.Graph(id="corr-chart", config={"displayModeBar": False})],
                                 className="grid-item-1-half",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                ],
                className="charts-grid-container",
                style={"padding": "18px 24px"}
            ),
        ])
    ])
