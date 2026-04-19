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
<style>
/* ── Theme tokens ── */
body[data-theme="dark"] {
  --bg: #111110; --surface: #1c1c1a; --border: rgba(255,255,255,0.08);
  --t-pri: #f0ede8; --t-sec: #8a8880;
  --green: #1D9E75; --red: #E24B4A;
  --danger: #E24B4A; --warning: #EF9F27; --info: #378ADD;
  color-scheme: dark;
}
body[data-theme="light"] {
  --bg: #ffffff; --surface: #f8f8f6; --border: rgba(0,0,0,0.09);
  --t-pri: #1a1a1a; --t-sec: #6b6b67;
  --green: #1D9E75; --red: #E24B4A;
  --danger: #E24B4A; --warning: #EF9F27; --info: #378ADD;
  color-scheme: light;
}
body {
  background-color: var(--bg) !important;
  color: var(--t-pri) !important;
}
input, select, button {
  background: var(--surface) !important;
  color: var(--t-pri) !important;
  border: 1px solid var(--border) !important;
}
input::placeholder { color: var(--t-sec) !important; }
.Select-control, .Select {
  background: var(--surface) !important; color: var(--t-pri) !important;
}
.Select input { background: transparent !important; color: var(--t-pri) !important; }
.Select-menu-outer, .Select .Select-menu-outer {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
}
.Select-option, .Select .Select-option {
  background: var(--surface) !important; color: var(--t-pri) !important;
}
.Select-option:hover, .Select .Select-option:hover { background: var(--bg) !important; }
.Select-value-label { color: var(--t-pri) !important; }
.Select-placeholder  { color: var(--t-sec) !important; }
a.ticker-link {
  color: var(--t-pri); text-decoration: none; font-weight: 500;
  border-bottom: 1px solid var(--border); transition: border-color 0.15s;
}
a.ticker-link:hover { border-color: var(--t-sec); }
a.nav-link {
  color: var(--t-sec); text-decoration: none;
  border: 0.5px solid var(--border); border-radius: 20px;
  padding: 3px 10px; font-size: 12px; transition: color 0.15s, border-color 0.15s;
}
a.nav-link:hover { color: var(--t-pri); border-color: var(--t-sec); }
details summary { color: var(--t-sec); }
@media print {
  #controls-bar, #txn-panel, #toggle-area,
  button, .Select, [id$="-btn"] { display: none !important; }
  body { background: white !important; }
  .js-plotly-plot { break-inside: avoid; }
  @page { size: A4 landscape; margin: 1.5cm; }
}
</style>
</head>
<body data-theme="dark">{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>
'''


from components.header import create_header

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
                style={
                    "display": "flex", "gap": "10px", "padding": "16px 24px",
                    "flexWrap": "wrap",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Transaction panel ─────────────────────────────────────────────
            html.Div(
                html.Div(
                    [
                        html.P("Add transaction",
                               style={"fontSize": "13px", "fontWeight": "500",
                                      "margin": "0 0 4px", "color": "var(--t-pri)"}),
                        html.P(
                            f"Saved to: {CSV_PATH}",
                            style={"fontSize": "11px", "color": "var(--t-sec)",
                                   "margin": "0 0 12px", "fontFamily": "monospace"},
                        ),
                        html.Div(
                            [
                                html.Div([
                                    html.P("Type", style={"fontSize": "11px",
                                                           "color": "var(--t-sec)",
                                                           "margin": "0 0 4px"}),
                                    dcc.Dropdown(
                                        id="txn-type",
                                        options=[{"label": "Buy",  "value": "buy"},
                                                 {"label": "Sell", "value": "sell"}],
                                        value="buy", clearable=False,
                                        style={"width": "100px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Ticker", style={"fontSize": "11px",
                                                             "color": "var(--t-sec)",
                                                             "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-ticker", type="text",
                                        placeholder="e.g. VHY",
                                        style={"width": "90px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Shares", style={"fontSize": "11px",
                                                             "color": "var(--t-sec)",
                                                             "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-shares", type="number", placeholder="0",
                                        style={"width": "90px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Price ($)", style={"fontSize": "11px",
                                                                "color": "var(--t-sec)",
                                                                "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-price", type="number", placeholder="0.00",
                                        style={"width": "100px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("Date (YYYY-MM-DD)",
                                           style={"fontSize": "11px",
                                                  "color": "var(--t-sec)",
                                                  "margin": "0 0 4px"}),
                                    dcc.Input(
                                        id="txn-date",
                                        type="text",
                                        placeholder=datetime.now().strftime("%Y-%m-%d"),
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                        debounce=True,
                                        style={"width": "120px", "fontSize": "13px"},
                                    ),
                                ]),
                                html.Div([
                                    html.P("\u00a0", style={"fontSize": "11px",
                                                             "margin": "0 0 4px"}),
                                    html.Button(
                                        "Add transaction", id="txn-submit", n_clicks=0,
                                        style={"fontWeight": "500", "fontSize": "13px",
                                               "padding": "7px 16px"},
                                    ),
                                ]),
                            ],
                            style={"display": "flex", "gap": "12px",
                                   "flexWrap": "wrap", "alignItems": "flex-end"},
                        ),
                        html.P(id="txn-msg",
                               style={"fontSize": "12px", "marginTop": "8px",
                                      "minHeight": "18px", "color": GREEN}),
                        html.Details([
                            html.Summary("Transaction history",
                                         style={"fontSize": "12px",
                                                "color": "var(--t-sec)",
                                                "cursor": "pointer",
                                                "marginTop": "8px"}),
                            html.Div(id="txn-log",
                                     style={"marginTop": "10px", "overflowX": "auto"}),
                        ]),
                    ],
                    style={
                        "padding":      "16px 18px",
                        "background":   "var(--surface)",
                        "border":       "0.5px solid var(--border)",
                        "borderRadius": "10px",
                    },
                ),
                style={
                    "padding": "0 24px 16px 24px",
                    "borderBottom": "0.5px solid var(--border)",
                },
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
                        style={"display": "flex", "gap": "8px", "marginLeft": "auto"}
                    ),
                ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px", "flexWrap": "wrap"}),
                html.Div([
                    html.Div(
                        [
                            html.P("View:", style={"fontSize": "12px",
                                                    "color": "var(--t-sec)",
                                                    "margin": "0 8px 0 0",
                                                    "alignSelf": "center"}),
                            html.Div(id="ticker-toggle-btns",
                                     style={"display": "flex", "gap": "6px",
                                            "flexWrap": "wrap"}),
                        ],
                        style={"display": "flex", "alignItems": "center",
                               "marginBottom": "12px", "flexWrap": "wrap"},
                    ),
                    dcc.Graph(id="pnl-history-chart",
                               config={"displayModeBar": False}),
                ]),
            ),

            # ── Charts grid ───────────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Price history — normalised to 100",
                                             "price-chart"),
                                 dcc.Graph(id="price-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "2", "minWidth": "280px"},
                            ),
                            html.Div(
                                [chart_title("Portfolio allocation", "allocation"),
                                 dcc.Graph(id="allocation-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "1", "minWidth": "220px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Unrealised P&L — all time", "pnl-bar"),
                                 dcc.Graph(id="pnl-bar-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Today's P&L", "day-pnl"),
                                 dcc.Graph(id="day-pnl-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap", "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [chart_title("Annual dividend income", "dividend"),
                                 dcc.Graph(id="dividend-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "1", "minWidth": "260px"},
                            ),
                            html.Div(
                                [chart_title("Return correlation matrix",
                                             "correlation"),
                                 dcc.Graph(id="corr-chart",
                                           config={"displayModeBar": False})],
                                 style={"flex": "1", "minWidth": "260px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "14px",
                               "flexWrap": "wrap"},
                    ),
                ],
                style={"padding": "16px 24px"},
            ),
        ],
    )