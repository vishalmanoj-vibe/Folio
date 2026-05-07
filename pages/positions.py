# pages/positions.py
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
            # ── Page Header ──────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Positions", className="header-title"),
                        html.P("Detailed view per ETF holding", className="header-subtitle"),
                    ], className="header-title-row"),
                    html.Div([
                        dmc.Button(
                            "Generate Signals",
                            id="generate-signals-btn",
                            variant="light",
                            color="teal",
                            size="sm",
                            leftSection="🤖"
                        ),
                        dcc.Loading(
                            id="loading-signals",
                            type="dot",
                            color="var(--t-pri)",
                            children=html.Span(
                                id="signals-status-label",
                                style={"marginLeft": "10px", "fontSize": "11px", "color": "var(--t-sec)"}
                            )
                        )
                    ], style={"marginLeft": "auto", "display": "flex", "alignItems": "center", "gap": "8px"})
                ],
                className="page-header-row",
                style={"display": "flex"}
            ),

            html.Div([
                # ── Holding Cards Grid ──────────────────────────────────────────
                section(None, html.Div(id="positions-card-grid", className="holding-card-grid")),

                # ── ETF Detail Panel ────────────────────────────────────────────
                # The section remains visible, but children are populated by callbacks.
                # Titles are moved into children to prevent empty headers on load.
                section(
                    html.Div(id="positions-detail-title"),
                    html.Div([
                        html.Div(id="etf-detail-cards", className="etf-detail-grid"),
                        html.Div(id="positions-tech-signals-container"),
                        html.Div(id="ai-insight-container"),
                        
                        # Price Chart Section (Dynamic)
                        html.Div(id="positions-price-chart-container"),

                        # Ticker-Specific Dividend History (Dynamic)
                        html.Div(id="positions-ticker-dividend-container"),

                        # Transaction Table (Dynamic)
                        html.Div(id="positions-txn-table-container"),

                    ], id="etf-detail-panel")
                ),

                # ── Portfolio Dividend Insights (Global) ─────────────────────────
                section(
                    None,
                    html.Details([
                        html.Summary("Portfolio Dividend Insights", className="txn-history-summary"),
                        html.Div([
                            html.Div([
                                html.Div([
                                    chart_title("Annual estimated income"),
                                    html.Div(id="positions-dividend-income-chart", className="dividend-progress-container"),
                                ], className="grid-item-1"),
                                html.Div([
                                    chart_title("Yield comparison (%)"),
                                    html.Div(id="positions-dividend-yield-chart", className="dividend-progress-container"),
                                ], className="grid-item-1"),
                            ], className="charts-grid-row", style={"marginTop": "20px"}),
                            html.Div([
                                chart_title("Recent global distributions"),
                                html.Div(id="positions-dividend-table", className="overflow-table", style={"marginTop": "10px"}),
                            ], style={"marginTop": "24px"}),
                        ], id="positions-dividend-insights-container")
                    ], id="positions-dividend-details")
                ),
            ])
        ],
        className="page-root"
    )
