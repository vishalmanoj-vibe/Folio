"""
pages/analytics.py
==================
Deep-dive charts and secondary metrics.
Route: /analytics
"""

import dash
from dash import html, dcc, Input, Output, State
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from components.header import create_header
from components.ui_helpers import chart_title, section
from config.constants import COLORS, T_SEC

dash.register_page(__name__, path="/analytics", title="Portfolio — Analytics")

def layout():
    return html.Div([
        # ── Header ────────────────────────────────────────────────────────
        create_header(
            title="Portfolio Analytics",
            subtitle="Allocation, Risk, and Performance deep-dive",
            links_before=[
                {"label": "Overview", "href": "/"}
            ],
            links_after=[
                {"label": "Intelligence", "href": "/intelligence"}
            ],
            show_pdf=True,
            market_status=html.Div(id="market-status")
        ),

        # ── Tabs Navigation ───────────────────────────────────────────────
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Allocation", value="allocation"),
                        dmc.TabsTab("Risk & Performance", value="performance"),
                        dmc.TabsTab("Income", value="income"),
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
                                    value="sector",
                                    size="xs",
                                    radius="xl"
                                ),
                            ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),
                            dcc.Loading(
                                dcc.Graph(id="portfolio-treemap", config={"displayModeBar": False}, style={"height": "600px"}),
                                type="circle", color=COLORS[0]
                            )
                        ),
                        
                        html.Div(
                            "The treemap above provides a hierarchical breakdown of your portfolio. "
                            "Size represents market value (allocation), while color shows percentage P&L performance. "
                            "Switch modes to see concentration risk by sector or region.",
                            style={"fontSize": "12px", "color": "var(--t-sec)", "marginTop": "10px", "textAlign": "center"}
                        )
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
                                    value="max",
                                    variant="unstyled",
                                    allowDeselect=False,
                                    persistence=True,
                                    style={"width": "120px", "marginLeft": "auto", "fontSize": "12px", "color": "var(--t-sec)"},
                                ),
                            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
                            dcc.Graph(id="price-chart", config={"displayModeBar": False}, style={"height": "400px"})
                        ),

                        # Row for Correlation & Volatility
                        section(
                            html.Div(), # Empty title node
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
                            ], className="charts-grid-row", style={"gap": "24px"})
                        )
                    ]),
                    value="performance"
                ),

                # ── Tab 3: Income ─────────────────────────────────────────────
                dmc.TabsPanel(
                    html.Div([
                        section(
                            chart_title("Dividend Income Detail", "div-desc"),
                            html.Div(
                                dcc.Graph(id="dividend-lollipops", config={"displayModeBar": False}),
                                style={"height": "550px", "overflowY": "auto", "borderRadius": "8px", "background": "var(--bg)"}
                            )
                        )
                    ]),
                    value="income"
                ),
            ],
            value="allocation",
            variant="default",
            className="analytics-tabs"
        ),
    ], className="page-root")
