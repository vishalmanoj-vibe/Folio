"""
pages/positions.py
==================
Positions overview page — card grid and detailed ETF breakdown.
Route: /positions
"""

import dash
from dash import html, dcc
import dash_mantine_components as dmc
from components.ui_helpers import section, chart_title

dash.register_page(__name__, path="/positions", title="Positions")

def layout() -> html.Div:
    return html.Div(
        [
            # Hidden store for the selected ticker
            dcc.Store(id="positions-selected-ticker", storage_type="session"),
            dcc.Store(id="positions-period-store", data="3mo", storage_type="session"),

            # ── Page Header ──────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Positions", className="header-title"),
                        html.P("Detailed view per ETF holding", className="header-subtitle"),
                    ], className="header-title-row"),
                ],
                className="page-header-row"
            ),

            html.Div([
                # ── Holding Cards Grid ──────────────────────────────────────────
                html.Div(id="positions-card-grid", className="holding-card-grid"),

                # ── ETF Detail Panel ────────────────────────────────────────────
                section(
                    None,
                    html.Div([
                        html.Div(id="etf-detail-cards", className="etf-detail-grid"),
                        
                        # Price Chart Section
                        html.Div([
                            html.Div([
                                chart_title("Price history", "positions-price"),
                                html.Div(id="positions-period-btns", className="flex-row-gap", style={"marginLeft": "auto"})
                            ], className="flex-row flex-center", style={"marginBottom": "12px"}),
                            dcc.Graph(id="positions-price-chart", config={"displayModeBar": False}),
                        ]),

                        # Transaction Table
                        html.Div([
                            chart_title("Transaction history", "positions-txns"),
                            html.Div(id="positions-txn-table", className="overflow-table", style={"marginTop": "10px"}),
                        ], style={"marginTop": "24px"}),

                    ], id="etf-detail-panel")
                ),
            ], className="page-container")
        ],
        className="page-root"
    )
