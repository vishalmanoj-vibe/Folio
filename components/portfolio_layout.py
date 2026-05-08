# components/portfolio_layout.py
"""
components/portfolio_layout.py
==============================
Portfolio page layout for the Overview page.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from datetime import datetime
from components.ui_helpers import chart_title, section
from config.settings import DB_PATH

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

            # ── Alerts banner ─────────────────────────────────────────────────
            html.Div(id="alerts-banner"),

            # ── Overview split: cards left | P&L chart right ──────────────────
            html.Div(
                [
                    # Left: stat cards (2-per-row, 3 rows)
                    html.Div(
                        id="stat-cards",
                        className="stat-cards-container",
                    ),

                    # Right: P&L chart with filters
                    html.Div(
                        [
                            # Chart header with title + period/mode dropdowns
                            html.Div([
                                chart_title("P&L history", "pnl-history"),
                                html.Div([
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
                                        className="header-dropdown",
                                        style={"width": "140px"}
                                    ),
                                    dmc.Select(
                                        id="pnl-mode",
                                        data=[
                                            {"label": "Dollar ($)",     "value": "dollar"},
                                            {"label": "Percentage (%)", "value": "pct"},
                                        ],
                                        value="pct",
                                        allowDeselect=False,
                                        className="header-dropdown",
                                        style={"width": "130px"}
                                    ),
                                ], className="pnl-controls-row"),
                            ], className="pnl-header-row"),

                            # Ticker selector + chart
                            html.Div([
                                html.Div([
                                    dmc.Select(
                                        id="ticker-selector",
                                        data=["Portfolio"],
                                        value="Portfolio",
                                        searchable=True,
                                        allowDeselect=False,
                                        size="xs",
                                        className="header-dropdown",
                                        style={"width": "160px"}
                                    ),
                                ], style={"marginBottom": "10px", "display": "flex", "justifyContent": "flex-start"}),
                                dcc.Graph(id="pnl-history-chart", config={"displayModeBar": False}),
                            ]),
                        ],
                        className="overview-chart-panel",
                    ),
                ],
                className="overview-split-row",
            ),

            # ── Live positions table ──────────────────────────────────────────
            section(
                chart_title("Live positions"),
                html.Div([
                    html.Div([
                        dmc.TextInput(
                            id="table-filter",
                            placeholder="Filter positions...",
                            size="xs",
                            leftSection=html.Span("🔍", style={"fontSize": "14px"}),
                            className="table-filter-input",
                            style={"width": "260px"},
                            persistence=True,
                        ),
                        
                        html.Button(
                            [html.Span("+", style={"fontSize": "16px", "fontWeight": "bold"}), "Add Transaction"],
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
                                        html.Div(className="txn-ticker-hint"),
                                    ], className="txn-input-container"),
                                    
                                    html.Div([
                                        html.P("Ticker", className="txn-label"),
                                        dmc.TextInput(id="txn-ticker", placeholder="VHY", className="txn-input-text", debounce=500),
                                        html.Div(id="txn-ticker-hint", className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                    html.Div([
                                        html.P("Shares", className="txn-label"),
                                        dmc.NumberInput(id="txn-shares", placeholder="0", min=0, className="txn-input-num"),
                                        html.Div(className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                    html.Div([
                                        html.P("Price", className="txn-label"),
                                        dmc.NumberInput(id="txn-price", placeholder="0.00", min=0, decimalScale=3, className="txn-input-num"),
                                        html.Div(className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                    html.Div([
                                        html.P("Date", className="txn-label"),
                                        dmc.DateInput(
                                            id="txn-date",
                                            value=datetime.now().date(),
                                            valueFormat="YYYY-MM-DD",
                                            className="txn-input-date",
                                        ),
                                        html.Div(className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                    html.Div([
                                        html.P("", className="txn-label"),
                                        html.Button("Add", id="txn-submit", n_clicks=0, className="btn-primary", style={"width": "120px", "height": "34px"}),
                                        html.Div(className="txn-ticker-hint"),
                                    ], className="txn-input-container"),

                                ], className="txn-form-grid", style={"border": "none", "background": "transparent", "padding": "0"}),
                                
                                html.P(id="txn-msg", className="txn-status-msg"),
                                
                                html.Details([
                                    html.Summary("View history log", className="txn-history-summary"),
                                    html.Div(id="txn-log", className="txn-history-log"),
                                ], id="txn-history-details"),
                                
                                html.P(f"Storage: {DB_PATH}", className="txn-path"),
                            ], className="card-inset", style={"marginBottom": "16px", "padding": "16px"}),
                        ]
                    ),

                    html.Div(id="live-table")
                ], style={"display": "flex", "flexDirection": "column"}),
            ),
        ],
        className="page-root"
    )