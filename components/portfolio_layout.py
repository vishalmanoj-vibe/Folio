"""
components/portfolio_layout.py
==============================
Portfolio page layout.

Changes from previous version
------------------------------
- Strip redundant CSS from INDEX_STRING (centralized in assets/).
- Migrate inline styles to CSS classes for modularity.
"""

from datetime import datetime
from dash import dcc, html
from config.settings import CSV_PATH
from components.ui_helpers import chart_title, section
from components.header import create_header

# ── CSS injected into <head> ───────────────────────────────────────────────────
INDEX_STRING = '''
<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
</head>
<body data-theme="dark">{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>
'''

def create_layout(initial_history: list[dict] | None = None) -> html.Div:
    """
    Construct the main dashboard layout.
    """
    return html.Div(
        [
            # ── Header ────────────────────────────────────────────────────────
            create_header(
                title="Portfolio — Live P&L",
                subtitle="Auto-refreshes every 60 s · Yahoo Finance · ASX ETFs",
                nav_links=[{"label": "Intelligence →", "href": "/intelligence"}],
                show_pdf=True,
                market_status=html.Div(id="market-status")
            ),

            # ── Stat cards ────────────────────────────────────────────────────
            html.Div(
                id="stat-cards",
                className="stat-cards-container",
            ),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Transaction panel ─────────────────────────────────────────────
            html.Div(
                html.Div(
                    [
                        html.P("Add transaction", className="txn-title"),
                        html.P(f"Saved to: {CSV_PATH}", className="txn-path"),
                        html.Div(
                            [
                                html.Div([
                                    html.P("Type", className="txn-label"),
                                    dcc.Dropdown(
                                        id="txn-type",
                                        options=[{"label": "Buy",  "value": "buy"},
                                                 {"label": "Sell", "value": "sell"}],
                                        value="buy", clearable=False,
                                        className="txn-dropdown",
                                    ),
                                ]),
                                html.Div([
                                    html.P("Ticker", className="txn-label"),
                                    dcc.Input(
                                        id="txn-ticker", type="text",
                                        placeholder="e.g. VHY",
                                        className="txn-input-text",
                                    ),
                                ]),
                                html.Div([
                                    html.P("Shares", className="txn-label"),
                                    dcc.Input(
                                        id="txn-shares", type="number", placeholder="0",
                                        className="txn-input-num",
                                    ),
                                ]),
                                html.Div([
                                    html.P("Price ($)", className="txn-label"),
                                    dcc.Input(
                                        id="txn-price", type="number", placeholder="0.00",
                                        className="txn-input-num",
                                    ),
                                ]),
                                html.Div([
                                    html.P("Date (YYYY-MM-DD)", className="txn-label"),
                                    dcc.Input(
                                        id="txn-date",
                                        type="text",
                                        placeholder=datetime.now().strftime("%Y-%m-%d"),
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                        debounce=True,
                                        className="txn-input-text",
                                    ),
                                ]),
                                html.Div([
                                    html.P("\u00a0", className="txn-label"),
                                    html.Button(
                                        "Add transaction", id="txn-submit", n_clicks=0,
                                        className="btn-md",
                                    ),
                                ]),
                            ],
                            className="txn-inputs-row",
                        ),
                        html.P(id="txn-msg", className="txn-status-msg"),
                        html.Details([
                            html.Summary("Transaction history", className="txn-history-summary"),
                            html.Div(id="txn-log", className="txn-history-log"),
                        ]),
                    ],
                    className="txn-panel-inner",
                ),
                className="txn-panel-container",
            ),

            # ── Live positions table ──────────────────────────────────────────
            section(chart_title("Live positions"), html.Div(id="live-table")),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                html.Div([
                    chart_title("P&L from purchase date", "pnl-history"),
                    html.Div(
                        [
                            dcc.Dropdown(
                                id="period-picker",
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
                                id="pnl-mode",
                                options=[
                                    {"label": "Dollar ($)",     "value": "dollar"},
                                    {"label": "Percentage (%)", "value": "pct"},
                                ],
                                value="dollar", clearable=False, searchable=False,
                                persistence=True, persistence_type="session",
                                style={"width": "130px", "fontSize": "12px"},
                            ),
                        ],
                        className="pnl-controls-row"
                    ),
                ], className="pnl-header-row"),
                html.Div([
                    html.Div(
                        [
                            html.P("View:", className="view-label"),
                            html.Div(id="ticker-toggle-btns", className="ticker-btns-row"),
                        ],
                        className="ticker-toggle-row",
                    ),
                    dcc.Graph(id="pnl-history-chart", config={"displayModeBar": False}),
                ]),
            ),

            # ── Charts grid ───────────────────────────────────────────────────
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
            ),
        ],
    )