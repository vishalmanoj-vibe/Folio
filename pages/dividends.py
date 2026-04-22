"""
pages/dividends.py
==================
Dividend income tracking and projections.
Route: /dividends
"""

import dash
from dash import html, dcc
import dash_mantine_components as dmc
from components.ui_helpers import section, chart_title

dash.register_page(__name__, path="/dividends", title="Dividends")

def layout() -> html.Div:
    return html.Div(
        [
            # ── Page Header ──────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Dividends", className="header-title"),
                        html.P("Historical distributions and income projections", className="header-subtitle"),
                    ], className="header-title-row"),
                ],
                className="page-header-row"
            ),

            html.Div([
                # ── KPI Row ───────────────────────────────────────────────────
                html.Div(id="dividend-stats-cards", className="stat-cards-container"),

                # ── Dividend Calendar ─────────────────────────────────────────────
                section(
                    chart_title("Dividend calendar", "div-calendar-tip"),
                    html.Div([
                        html.Div(id="dividend-calendar", className="dividend-calendar-grid"),
                        html.P("Estimated dates based on trailing 12-month distribution schedule", 
                               style={"fontSize": "11px", "color": "var(--t-muted)", "marginTop": "12px"})
                    ]),
                ),

                # ── Analysis Charts (Two-Column) ────────────────────────────────
                html.Div([
                    html.Div([
                        section(
                            chart_title("Annual estimated income by ETF"),
                            dcc.Graph(id="dividend-income-chart", config={"displayModeBar": False}),
                        )
                    ], className="grid-item-1"),
                    html.Div([
                        section(
                            chart_title("Yield comparison (%)"),
                            dcc.Graph(id="dividend-yield-chart", config={"displayModeBar": False}),
                        )
                    ], className="grid-item-1"),
                ], className="charts-grid-row"),


                # ── Distribution Log Table ──────────────────────────────────────
                section(
                    chart_title("All-time distribution log"),
                    html.Div(id="dividend-table", className="overflow-table", style={"marginTop": "10px"}),
                ),
            ], className="page-container")
        ],
        className="page-root"
    )
