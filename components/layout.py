from datetime import datetime
from dash import dcc, html
from config import BORDER, T_SEC, GREEN, REFRESH_INTERVAL, CSV_PATH
from components.ui_helpers import chart_title, section

def create_layout(initial_history: list[dict] | None = None) -> html.Div:
    """
    Build and return the full Dash layout tree.
    Pass initial_history to pre-seed the txn-store on startup.
    """
    return html.Div(
        [
            # ── Stores & interval ─────────────────────────────────────────────
            dcc.Store(id="txn-store",       data=initial_history or []),
            dcc.Store(id="portfolio-store"),
            dcc.Store(id="alerts-store"),
            dcc.Store(id="theme-store",     data="dark"),
            dcc.Interval(id="live-interval", interval=REFRESH_INTERVAL, n_intervals=0),

            # ── Header ────────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1(
                            "Portfolio — Live P&L",
                            style={"margin": "0", "fontSize": "20px", "fontWeight": "500"},
                        ),
                        html.P(
                            "Auto-refreshes every 60 s · Yahoo Finance · ASX ETFs",
                            style={"margin": "3px 0 0", "fontSize": "12px", "color": T_SEC},
                        ),
                        html.Button(
                            "☀ / ☾", id="theme-toggle", n_clicks=0,
                            style={"fontSize": "12px", "padding": "4px 10px"},
                        ),
                    ]),
                    html.Div(
                        [
                            html.Div(id="market-status"),
                            html.Span(id="last-updated", style={"fontSize": "12px", "color": T_SEC}),
                        ],
                        style={"display": "flex", "flexDirection": "column",
                               "alignItems": "flex-end", "gap": "6px"},
                    ),
                ],
                style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "flex-start", "padding": "18px 24px 12px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Controls bar ─────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.P("Chart period", style={"fontSize": "12px", "color": T_SEC, "margin": "0 0 4px"}),
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
                            value="3mo", clearable=False,
                            style={"width": "155px", "fontSize": "13px"},
                        ),
                    ]),
                    html.Div([
                        html.P("P&L view", style={"fontSize": "12px", "color": T_SEC, "margin": "0 0 4px"}),
                        dcc.Dropdown(
                            id="pnl-mode",
                            options=[
                                {"label": "Dollar ($)",     "value": "dollar"},
                                {"label": "Percentage (%)", "value": "pct"},
                            ],
                            value="dollar", clearable=False,
                            style={"width": "155px", "fontSize": "13px"},
                        ),
                    ]),
                    html.Button(
                        "Refresh now", id="refresh-btn", n_clicks=0,
                        style={"fontWeight": "500", "alignSelf": "flex-end"},
                    ),
                    html.Button(
                        "⬇ Download PDF", id="pdf-btn", n_clicks=0,
                        style={"fontWeight": "500", "alignSelf": "flex-end"},
                    ),
                ],
                style={
                    "display": "flex", "gap": "16px", "alignItems": "flex-end",
                    "padding": "14px 24px", "borderBottom": "0.5px solid var(--border)",
                    "flexWrap": "wrap",
                },
            ),

            # ── Stat cards — row 1: portfolio summary ─────────────────────────
            html.Div(
                id="stat-cards",
                style={
                    "display": "flex", "gap": "10px", "padding": "16px 24px 8px",
                    "flexWrap": "wrap",
                },
            ),

            # ── Stat cards — row 2: best / worst performer ────────────────────
            html.Div(
                id="stat-cards-performers",
                style={
                    "display": "flex", "gap": "10px", "padding": "0 24px 16px",
                    "flexWrap": "wrap", "borderBottom": f"0.5px solid {BORDER}",
                },
            ),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Transaction panel ─────────────────────────────────────────────
            section(
                chart_title("Add transaction"),
                html.Div(
                    [
                        html.P(
                            f"Saved to: {CSV_PATH}",
                            style={
                                "fontSize": "11px",
                                "color": "var(--t-sec)",
                                "margin": "0 0 12px",
                                "fontFamily": "monospace",
                            },
                        ),

                        html.Div(
                            [
                                html.Div([
                                    html.P("Type", style={"fontSize": "11px", "color": "var(--t-sec)", "margin": "0 0 4px"}),
                                    dcc.Dropdown(
                                        id="txn-type",
                                        options=[
                                            {"label": "Buy", "value": "buy"},
                                            {"label": "Sell", "value": "sell"},
                                        ],
                                        value="buy",
                                        clearable=False,
                                        style={"width": "100px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Ticker", style={"fontSize": "11px", "color": "var(--t-sec)", "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-ticker",
                                        type="text",
                                        placeholder="e.g. VHY",
                                        style={"width": "90px", "fontSize": "13px", "padding": "6px 8px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Shares", style={"fontSize": "11px", "color": "var(--t-sec)", "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-shares",
                                        type="number",
                                        placeholder="0",
                                        style={"width": "90px", "fontSize": "13px", "padding": "6px 8px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Price ($)", style={"fontSize": "11px", "color": "var(--t-sec)", "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-price",
                                        type="number",
                                        placeholder="0.00",
                                        style={"width": "100px", "fontSize": "13px", "padding": "6px 8px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Date", style={"fontSize": "11px", "color": "var(--t-sec)", "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-date",
                                        type="text",
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                        style={"width": "130px", "fontSize": "13px", "padding": "6px 8px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("\u00a0"),
                                    html.Button(
                                        "Add transaction",
                                        id="txn-submit",
                                        n_clicks=0,
                                        style={"fontWeight": "500", "padding": "7px 16px"},
                                    ),
                                ]),
                            ],
                            style={
                                "display": "flex",
                                "gap": "12px",
                                "flexWrap": "wrap",
                                "alignItems": "flex-end",
                            },
                        ),

                        html.P(
                            id="txn-msg",
                            style={
                                "fontSize": "12px",
                                "marginTop": "10px",
                                "minHeight": "18px",
                                "color": GREEN,
                            },
                        ),

                        html.Details([
                            html.Summary(
                                "Transaction history",
                                style={
                                    "fontSize": "12px",
                                    "color": "var(--t-sec)",
                                    "cursor": "pointer",
                                    "marginTop": "10px",
                                },
                            ),
                            html.Div(id="txn-log", style={"marginTop": "10px"}),
                        ]),
                    ]
                ),
            ),

            # ── Live positions table ──────────────────────────────────────────
            section(
                chart_title("Live positions"),
                dcc.Loading(
                    children=[html.Div(id="live-table")],
                    type="circle",
                    color="#378ADD",
                ),
            ),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                chart_title("P&L from purchase date", "pnl-history"),
                html.Div([
                    html.Div(
                        [
                            html.P("View:", style={"fontSize": "12px", "color": T_SEC,
                                                    "margin": "0 8px 0 0", "alignSelf": "center"}),
                            html.Div(id="ticker-toggle-btns",
                                     style={"display": "flex", "gap": "6px", "flexWrap": "wrap"}),
                        ],
                        style={"display": "flex", "alignItems": "center",
                               "marginBottom": "12px", "flexWrap": "wrap"},
                    ),
                    dcc.Graph(id="pnl-history-chart", config={"displayModeBar": False}),
                ]),
            ),

            # ── Charts grid ───────────────────────────────────────────────────
            html.Div(
                [
                    # Row 1: price history + allocation donut
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Price history — normalised to 100", "price-chart"),
                                 dcc.Graph(id="price-chart", config={"displayModeBar": False})],
                                style={"flex": "2", "minWidth": "280px"},
                            ),
                            html.Div(
                                [chart_title("Portfolio allocation", "allocation"),
                                 dcc.Graph(id="allocation-chart", config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "220px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    # Row 2: all-time P&L bar + day P&L bar
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 dcc.Graph(id="pnl-bar-chart", config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 dcc.Graph(id="day-pnl-chart", config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    # Row 3: dividends + correlation heatmap
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 dcc.Graph(id="dividend-chart", config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Return correlation matrix", "correlation"),
                                 dcc.Graph(id="corr-chart", config={"displayModeBar": False})],
                                style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                    ),
                ],
                style={"padding": "16px 24px"},
            ),
        ],
        style={
            "fontFamily":      "system-ui,-apple-system,sans-serif",
            "color":           "var(--t-pri)",
            "maxWidth":        "1300px",
            "margin":          "0 auto",
            "backgroundColor": "var(--bg)",
            "minHeight":       "100vh",
        },
    )