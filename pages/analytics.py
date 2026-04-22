"""
pages/analytics.py
==================
Deep-dive charts and secondary metrics.
Route: /analytics
"""

import dash
from dash import html, dcc
import dash_mantine_components as dmc
from components.ui_helpers import chart_title, section
from config.constants import COLORS

dash.register_page(__name__, path="/analytics", title="Analytics")

def layout():
    return html.Div([
        # ── Page Header Row ───────────────────────────────────────────────
        html.Div(
            [
                html.Div([
                    html.H1("Analytics", className="header-title"),
                    html.P("Allocation, risk & performance deep-dive", className="header-subtitle"),
                ], className="header-title-row"),
                html.Div([
                    # Standalone export button removed to avoid duplicate ID with global nav
                ], className="header-controls"),
            ],
            className="page-header-row"
        ),

        # ── Tabs Navigation ───────────────────────────────────────────────
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Allocation", value="allocation"),
                        dmc.TabsTab("Risk & Performance", value="performance"),
                    ],
                    className="tabs-list-custom"
                ),

                # ── Tab 1: Allocation ─────────────────────────────────────────
                dmc.TabsPanel(
                    html.Div([
                        # Treemap with Hierarchy Toggle
                        section(
                            html.Div([
                                chart_title("Portfolio Allocation Breakdown", "treemap-desc"),
                                html.Div(style={"flex": "1"}),
                                dmc.SegmentedControl(
                                    id="treemap-mode",
                                    data=[
                                        {"label": "Flat Tickers", "value": "flat"},
                                        {"label": "By Sector", "value": "sector"},
                                        {"label": "By Region", "value": "geo"},
                                    ],
                                    value="flat",
                                    size="xs",
                                    radius="xl"
                                ),
                            ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),
                            html.Div([
                                dcc.Loading(
                                    dcc.Graph(id="portfolio-treemap", config={"displayModeBar": False}, style={"height": "600px"}),
                                    type="circle", color=COLORS[0]
                                ),
                                html.Div(
                                    "Colour encodes P&L performance. Size encodes market value.",
                                    style={"fontSize": "11px", "color": "var(--t-muted)", "marginTop": "12px", "textAlign": "center"}
                                )
                            ])
                        ),
                    ]),
                    value="allocation"
                ),

                # ── Tab 2: Performance & Risk ─────────────────────────────────
                dmc.TabsPanel(
                    html.Div([
                        # Price History
                        section(
                            html.Div([
                                chart_title("Price History — Normalised to 100", "price-chart-desc"),
                                dmc.SegmentedControl(
                                    id="analytics-period-picker",
                                    data=[
                                        {"label": "Since purchase", "value": "max"},
                                        {"label": "1M", "value": "1mo"},
                                        {"label": "3M", "value": "3mo"},
                                        {"label": "6M", "value": "6mo"},
                                        {"label": "1Y", "value": "1y"},
                                    ],
                                    value="max",
                                    size="sm",
                                    radius="lg",
                                    className="period-segmented-control"
                                ),
                            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
                            dcc.Graph(id="price-chart", config={"displayModeBar": False}, style={"height": "400px"})
                        ),

                        # Row for Correlation & Volatility
                        section(
                            None, # No title node
                            html.Div([
                                html.Div([
                                    chart_title("Return Correlation Matrix", "corr-desc"),
                                    dcc.Graph(id="corr-chart", config={"displayModeBar": False})
                                ], className="grid-item-1"),
                                html.Div([
                                    chart_title("Volatility by ETF", "vol-desc"),
                                    dcc.Loading(
                                        dcc.Graph(id="analytics-vol-chart", config={"displayModeBar": False}),
                                        type="circle", color=COLORS[2]
                                    )
                                ], className="grid-item-1"),
                            ], className="charts-grid-row")
                        )
                    ]),
                    value="performance"
                ),

            ],
            value="allocation",
            variant="default",
            className="analytics-tabs"
        ),
    ], className="page-root")
