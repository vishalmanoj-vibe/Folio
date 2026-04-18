"""
components/portfolio_layout.py
==============================
Portfolio page layout.

Changes from previous version
------------------------------
- Header now includes an "Intelligence →" nav link next to the title.
  All other structure is unchanged.
"""

from datetime import datetime
from dash import dcc, html
from config.constants import GREEN
from config.settings import CSV_PATH
from components.ui_helpers import chart_title, section

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

    Args:
        initial_history: Pre-fetched transaction history to inject into stores on load.

    Returns:
        A Dash html.Div containing the full layout and dcc.Stores.
    """
    return html.Div(
        [
            # ── Header ────────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        # Title row with nav link
                        html.Div(
                            [
                                html.H1("Portfolio — Live P&L", className="header-title"),
                                html.A("Intelligence →", href="/intelligence", className="nav-link"),
                            ],
                            className="header-title-row",
                        ),
                        html.P("Auto-refreshes every 60 s · Yahoo Finance · ASX ETFs", className="header-subtitle"),
                    ]),
                    html.Div(
                        [
                            html.Div(id="market-status"),
                            html.Span(id="last-updated", className="header-last-updated"),
                            html.Div(
                                [
                                    html.Button("☀ / ☾", id="theme-toggle", n_clicks=0, className="btn-toggle"),
                                    html.Button("Refresh now", id="refresh-btn", n_clicks=0, className="btn-sm"),
                                    html.Button("⬇ PDF", id="pdf-btn", n_clicks=0, className="btn-sm"),
                                ],
                                className="header-btn-group",
                            ),
                        ],
                        className="header-controls",
                    ),
                ],
                className="header-container",
            ),

            # ── Stat cards ────────────────────────────────────────────────────
            html.Div(id="stat-cards", className="stat-cards-container"),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Transaction panel ─────────────────────────────────────────────
            section(
                chart_title("Add transaction"),
                html.Div(
                    [
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
                                        className="txn-input-text",
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
                                        id="txn-date", type="text",
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                        className="txn-input-date",
                                    ),
                                ]),
                                html.Div([
                                    html.P("\u00a0", style={"fontSize": "11px", "margin": "0 0 4px"}),
                                    html.Button("Add transaction", id="txn-submit", n_clicks=0, className="btn-md"),
                                ]),
                            ],
                            className="txn-input-group",
                        ),
                        html.P(id="txn-msg", className="txn-msg", style={"color": GREEN}),
                        html.Details([
                            html.Summary("Transaction history", className="txn-summary"),
                            html.Div(id="txn-log", className="txn-log-container"),
                        ]),
                    ]
                )
            ),

            # ── Live positions table ──────────────────────────────────────────
            section(chart_title("Live positions"), html.Div(id="live-table")),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                chart_title("P&L", "pnl-history"),
                html.Div([
                    # Filters bar
                    html.Div(
                        [
                            html.Div([
                                html.P("Chart period", className="filter-label"),
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
                                    value="max", clearable=False,
                                    persistence=True, persistence_type="session",
                                    className="filter-dropdown",
                                ),
                            ]),
                            html.Div([
                                html.P("P&L view", className="filter-label"),
                                dcc.Dropdown(
                                    id="pnl-mode",
                                    options=[
                                        {"label": "Dollar ($)",     "value": "dollar"},
                                        {"label": "Percentage (%)", "value": "pct"},
                                    ],
                                    value="dollar", clearable=False,
                                    persistence=True, persistence_type="session",
                                    className="filter-dropdown",
                                ),
                            ]),
                        ],
                        className="filters-bar",
                    ),
                    # Ticker view toggles
                    html.Div(
                        [
                            html.P("View:", className="ticker-toggle-label"),
                            html.Div(id="ticker-toggle-btns", className="ticker-btn-group"),
                        ],
                        className="ticker-toggles",
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
                                className="chart-col-2",
                            ),
                            html.Div(
                                [chart_title("Portfolio allocation", "allocation"),
                                 dcc.Graph(id="allocation-chart", config={"displayModeBar": False})],
                                className="chart-col-1",
                            ),
                        ],
                        className="chart-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 dcc.Graph(id="pnl-bar-chart", config={"displayModeBar": False})],
                                className="chart-col-min-260",
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 dcc.Graph(id="day-pnl-chart", config={"displayModeBar": False})],
                                className="chart-col-min-260",
                            ),
                        ],
                        className="chart-row",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 dcc.Graph(id="dividend-chart", config={"displayModeBar": False})],
                                className="chart-col-min-260",
                            ),
                            html.Div(
                                [chart_title("Return correlation matrix", "correlation"),
                                 dcc.Graph(id="corr-chart", config={"displayModeBar": False})],
                                className="chart-col-min-260",
                            ),
                        ],
                        className="chart-row-last",
                    ),
                ],
                className="chart-grid",
            ),
        ],
    )