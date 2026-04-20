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

        # ── Charts Grid ───────────────────────────────────────────────────
        html.Div([
            html.Div(
                [
                    # Top Row: Unified Portfolio Performance (Scalable Treemap)
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Portfolio Performance & Allocation", "portfolio-performance"),
                                 dcc.Graph(id="portfolio-treemap", config={"displayModeBar": False})],
                                 className="grid-full-width",
                            ),
                        ],
                        className="charts-grid-row",
                    ),
                    
                    # Middle Row: Detailed Performance (Lollipops) & Correlation Matrix
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Dividend Income Detail", "dividend"),
                                 html.Div(
                                     dcc.Graph(id="dividend-lollipops", config={"displayModeBar": False}),
                                     style={"height": "400px", "overflowY": "auto", "borderRadius": "8px", "background": "#111110"}
                                 )],
                                 className="grid-item-1", 
                            ),
                            html.Div(
                                [chart_title("Return Correlation Matrix", "correlation"),
                                 dcc.Graph(id="corr-chart", config={"displayModeBar": False})],
                                 className="grid-item-1",
                            ),
                        ],
                        className="charts-grid-row",
                    ),

                    # Bottom Row: Price History (Full Width)
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            chart_title("Price history — normalised to 100", "price-chart"),
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
                                        ],
                                        style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}
                                    ),
                                    dcc.Graph(
                                        id="price-chart", 
                                        config={"displayModeBar": False},
                                        style={"height": "480px"}
                                    )
                                ],
                                className="grid-full-width",
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
