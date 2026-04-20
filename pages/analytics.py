"""
pages/analytics.py
==================
Deep-dive charts and secondary metrics.
Route: /analytics
"""

import dash
from dash import html, dcc
import dash_mantine_components as dmc
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
                        dmc.Select(
                            id="analytics-period-picker",
                            data=[
                                {"label": "Since purchase", "value": "max"},
                                {"label": "1 month",        "value": "1mo"},
                                {"label": "3 months",       "value": "3mo"},
                                {"label": "6 months",       "value": "6mo"},
                                {"label": "1 year",         "value": "1y"},
                                {"label": "2 years",        "value": "2y"},
                            ],
                            value="3mo",
                            allowDeselect=False,
                            persistence=True,
                            style={"width": "130px"},
                        ),
                        dmc.Select(
                            id="analytics-pnl-mode",
                            data=[
                                {"label": "Dollar ($)",     "value": "dollar"},
                                {"label": "Percentage (%)", "value": "pct"},
                            ],
                            value="dollar",
                            allowDeselect=False,
                            persistence=True,
                            style={"width": "130px"},
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
                                 html.Div(id="allocation-chart-container")],
                                 className="grid-item-1",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 html.Div(id="pnl-bar-chart-container")],
                                 className="grid-item-1-half",
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 html.Div(id="day-pnl-chart-container")],
                                 className="grid-item-1-half",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 html.Div(id="dividend-chart-container")],
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
