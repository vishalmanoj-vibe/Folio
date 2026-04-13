from datetime import datetime
from dash import dcc, html
from config import BG, SURFACE, BORDER, T_SEC, GREEN, REFRESH_INTERVAL, CSV_PATH
from components.ui_helpers import chart_title, section

# ── CSS injected into <head> ───────────────────────────────────────────────────
INDEX_STRING = '''
<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; }

/* ── Dark / light theme vars — applied to html AND body so full page is covered ── */
html, body[data-theme="dark"] {
  --bg: #111110; --surface: #1c1c1a; --border: rgba(255,255,255,0.08);
  --t-pri: #f0ede8; --t-sec: #8a8880;
}
body[data-theme="light"] {
  --bg: #ffffff; --surface: #f8f8f6; --border: rgba(0,0,0,0.09);
  --t-pri: #1a1a1a; --t-sec: #6b6b67;
}

/* ── Full page background always follows theme ── */
html {
  background-color: #111110;
}
body {
  margin: 0;
  background-color: var(--bg) !important;
  color: var(--t-pri);
  transition: background-color 0.2s ease, color 0.2s ease;
}

/* ── React root fills full viewport ── */
#react-entry-point, ._dash-loading {
  min-height: 100vh;
  background-color: var(--bg);
}

/* ── Form elements inherit theme ── */
input, select, button {
  background: var(--surface) !important;
  color: var(--t-pri) !important;
  border: 1px solid var(--border) !important;
}
input::placeholder { color: var(--t-sec) !important; }
.Select { background: var(--surface) !important; color: var(--t-pri) !important; }
.Select input { background: transparent !important; color: var(--t-pri) !important; }
.Select .Select-menu-outer {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}
.Select .Select-option { background: var(--surface) !important; color: var(--t-pri) !important; }
.Select .Select-option:hover { background: var(--bg) !important; }

/* ── Print / PDF — A4 landscape, graphs scale to fit ── */
@media print {
  /* Hide UI controls */
  #controls-bar, #txn-panel, #toggle-area,
  button, .Select, [id$="-btn"],
  .dash-loading-callback { display: none !important; }

  /* Full white page */
  html, body {
    background: white !important;
    color: black !important;
    margin: 0 !important;
  }

  /* Remove max-width constraint so content fills the page */
  body > div, #react-entry-point > div, #react-entry-point > div > div {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  /* Each chart block fits on the page */
  .js-plotly-plot {
    break-inside: avoid;
    width: 100% !important;
    max-width: 100% !important;
  }

  /* Charts fill their containers */
  .js-plotly-plot .plotly, .js-plotly-plot .plotly svg {
    width: 100% !important;
    height: auto !important;
  }

  /* Two charts per row on landscape A4 */
  @page {
    size: A4 landscape;
    margin: 1cm 1.5cm;
  }
}
/* ── Stat card hover (NEW) ── */
div[data-hover="true"]:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 14px rgba(0,0,0,0.10);
}
</style>
</head>
<body data-theme="dark">{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>
'''


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