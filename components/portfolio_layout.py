"""
components/portfolio_layout.py
==============================
Portfolio page layout for the Overview page.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from datetime import datetime
from components.ui_helpers import chart_title, section
from config.settings import CSV_PATH

# ── CSS injected into <head> ───────────────────────────────────────────────────
INDEX_STRING = '''
<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
    <script>
        (function() {
            try {
                const stored = localStorage.getItem('theme-store');
                if (stored) {
                    const theme = JSON.parse(stored);
                    document.documentElement.setAttribute('data-theme', theme);
                    document.body.setAttribute('data-theme', theme);
                    document.documentElement.style.backgroundColor = theme === 'dark' ? '#0a0a0a' : '#f5f7f7';
                }
            } catch (e) {}
        })();
    </script>
</head>
<body data-theme="dark">{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>
'''

def create_layout(initial_history: list[dict] | None = None) -> html.Div:
    """
    Construct the main dashboard overview layout.
    """
    return html.Div(
        [
            # ── Page Header Row ───────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Portfolio overview", className="header-title"),
                        html.P("Live P&L · Yahoo Finance · ASX ETFs", className="header-subtitle"),
                    ], className="header-title-row"),
                    html.Div([
                        # Header button removed to consolidate into table-level toggle
                    ], className="header-controls"),
                ],
                className="page-header-row"
            ),

            # ── Stat cards ────────────────────────────────────────────────────
            html.Div(
                id="stat-cards",
                className="stat-cards-container",
            ),

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Live positions table ──────────────────────────────────────────
            section(
                chart_title("Live positions"),
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("🔍", style={
                                "position": "absolute", 
                                "left": "10px", 
                                "top": "50%", 
                                "transform": "translateY(-50%)", 
                                "opacity": "0.4", 
                                "fontSize": "13px",
                                "zIndex": "1",
                                "pointerEvents": "none"
                            }),
                            dmc.TextInput(
                                id="table-filter",
                                placeholder="Filter positions...",
                                size="xs",
                                className="table-filter-input",
                                style={"width": "260px"},
                                styles={"input": {"paddingLeft": "32px"}},
                                persistence=True,
                            ),
                        ], style={"position": "relative"}),
                        
                        html.Button(
                            "+ Add transaction",
                            id="compact-toggle-btn",
                            n_clicks=0,
                            className="btn-primary btn-sm"
                        ),
                    ], className="table-controls-row"),

                    # ── Quick-Add Form (Collapsed) ────────────────────────────
                    dmc.Collapse(
                        id="txn-collapse",
                        opened=False,
                        children=[
                            html.Div([
                                html.Div([
                                    # Type & Ticker
                                    html.Div([
                                        html.P("Type", className="txn-label"),
                                        dmc.Select(
                                            id="txn-type",
                                            data=[{"label": "Buy",  "value": "buy"},
                                                  {"label": "Sell", "value": "sell"}],
                                            value="buy",
                                            allowDeselect=False,
                                            className="txn-dropdown",
                                        ),
                                    ], className="txn-input-container"),
                                    
                                    html.Div([
                                        html.P("Ticker", className="txn-label"),
                                        dmc.TextInput(id="txn-ticker", placeholder="VHY", className="txn-input-text"),
                                        html.Div(id="txn-ticker-hint", className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                    # Shares & Price
                                    html.Div([
                                        html.P("Shares", className="txn-label"),
                                        dmc.NumberInput(id="txn-shares", placeholder="0", min=0, className="txn-input-num"),
                                    ], className="txn-input-container"),

                                    html.Div([
                                        html.P("Price", className="txn-label"),
                                        dmc.NumberInput(id="txn-price", placeholder="0.00", min=0, decimalScale=3, className="txn-input-num"),
                                    ], className="txn-input-container"),

                                    # Date
                                    html.Div([
                                        html.P("Date", className="txn-label"),
                                        dmc.DateInput(
                                            id="txn-date",
                                            value=datetime.now().date(),
                                            valueFormat="YYYY-MM-DD",
                                            className="txn-input-date",
                                        ),
                                    ], className="txn-input-container"),

                                    # Submit
                                    html.Div([
                                        html.Button("Add", id="txn-submit", n_clicks=0, className="btn-primary btn-sm", style={"width": "120px"}),
                                    ], style={"alignSelf": "flex-end", "paddingBottom": "2px"}),

                                ], className="txn-form-grid", style={"border": "none", "background": "transparent", "padding": "0"}),
                                
                                html.P(id="txn-msg", className="txn-status-msg"),
                                
                                # History Detail
                                html.Details([
                                    html.Summary("View history log", className="txn-history-summary"),
                                    html.Div(id="txn-log", className="txn-history-log"),
                                ], id="txn-history-details"),
                                
                                html.P(f"Storage: {CSV_PATH}", className="txn-path"),
                            ], className="card-inset", style={"marginBottom": "16px", "padding": "16px"}),
                        ]
                    ),

                    html.Div(id="live-table")
                ], style={"display": "flex", "flexDirection": "column"}),
            ),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                html.Div([
                    chart_title("P&L history", "pnl-history"),
                    html.Div(
                        [
                            dmc.Select(
                                id="period-picker",
                                data=[
                                    {"label": "Today",          "value": "1d"},
                                    {"label": "Since purchase", "value": "max"},
                                    {"label": "1 month",        "value": "1mo"},
                                    {"label": "3 months",       "value": "3mo"},
                                    {"label": "6 months",       "value": "6mo"},
                                    {"label": "1 year",         "value": "1y"},
                                    {"label": "2 years",        "value": "2y"},
                                ],
                                value="max",
                                allowDeselect=False,
                                persistence=False,
                                style={"width": "130px"},
                            ),
                            dmc.Select(
                                id="pnl-mode",
                                data=[
                                    {"label": "Dollar ($)",     "value": "dollar"},
                                    {"label": "Percentage (%)", "value": "pct"},
                                ],
                                value="dollar",
                                allowDeselect=False,
                                persistence=True,
                                style={"width": "130px"},
                            ),
                        ],
                        className="pnl-controls-row"
                    ),
                ], className="pnl-header-row"),
                html.Div([
                    html.Div(
                        [
                            html.P("View:", className="view-label"),
                            html.Div([
                                dmc.Select(
                                    id="ticker-selector",
                                    data=["Portfolio"],
                                    value="Portfolio",
                                    searchable=True,
                                    allowDeselect=False,
                                    size="xs",
                                    className="ticker-selector-dropdown",
                                    style={"width": "160px"}
                                ),
                            ], id="ticker-selector-container"),
                        ],
                        className="ticker-toggle-row",
                    ),
                    dcc.Graph(id="pnl-history-chart", config={"displayModeBar": False}),
                ]),
            ),
        ],
        className="page-root"
    )