# pages/intelligence.py
"""
pages/intelligence.py
======================
Portfolio Intelligence page — risk analytics and return forecasting.
Route: /intelligence
"""

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html, register_page
from config.constants import COLORS, RED
from components.ui_helpers import section, chart_title

register_page(__name__, path="/intelligence", title="Intelligence")

def layout() -> html.Div:
    return html.Div(
        [
            # ── Page Header Row ───────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Intelligence", className="header-title"),
                        html.P("Risk metrics, equity curve & smart alerts", className="header-subtitle"),
                    ], className="header-title-row"),
                ],
                className="page-header-row"
            ),

            # ── Data source note ──────────────────────────────────────────────
            html.Div(id="intel-data-note", className="intel-data-note"),

            html.Div([
                # ── A. Risk scorecard ─────────────────────────────────────────────
                section(
                    chart_title(
                        "Risk metrics",
                        "Key risk stats calculated from the price history window. "
                        "Hover each card for an explanation of what the number means.",
                    ),
                    html.Div(id="intel-risk-cards", className="metrics-row"),
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
                                        html.Span("Forecast", id="intel-forecast-label", style={"marginRight": "10px", "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "500"}),
                                        dmc.Switch(
                                            id="intel-pred-toggle",
                                            checked=False,
                                            size="sm",
                                            color="cyan",
                                            className="forecast-switch",
                                            styles={
                                                "track": {"cursor": "pointer"},
                                                "thumb": {"backgroundColor": "#fff"}
                                            }
                                        ),
                                    ], style={"display": "flex", "alignItems": "center", "marginRight": "16px"}),
                                    
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
                                        style={"width": "125px"},
                                    ),
                                ], 
                                style={"display": "flex", "alignItems": "center", "marginLeft": "auto"}
                            ),
                        ],
                        className="pnl-header-row"
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
                        "How far your portfolio has fallen from its peak at any point in time.",
                    ),
                    dcc.Loading(
                        dcc.Graph(id="intel-drawdown-chart", config={"displayModeBar": False}),
                        type="circle", color=RED,
                    ),
                ),

                # ── D. Smart alerts ───────────────────────────────────────────────
                html.Div(
                    [
                        chart_title(
                            "Smart alerts",
                            "Rule-based insights from holdings, allocation weights, and risk metrics.",
                        ),
                        html.Div(id="intel-alerts", style={"marginTop": "10px"}),
                    ],
                    style={"padding": "16px 24px"}
                ),

                # ── E. Technical signals ───────────────────────────────────────────
                html.Div([
                    html.Div([
                        html.Span(
                            "Technical Signals",
                            className="chart-title-text"
                        ),
                        html.Span(
                            " · RSI, MACD, Bollinger Bands computed from price history",
                            style={"fontSize": "10px",
                                   "color": "var(--t-sec)",
                                   "marginLeft": "8px"}
                        ),
                    ], className="chart-title-container",
                       style={"marginBottom": "12px"}),
                    html.Div(id="intel-signals-table"),
                ], className="section-container", style={"padding": "16px 24px"}),
            ], className="page-container")
        ],
        className="page-root"
    )