"""
components/portfolio_layout.py
==============================
Portfolio page layout.
"""

from datetime import datetime
from dash import dcc, html
import dash_mantine_components as dmc
from config.settings import CSV_PATH
from components.ui_helpers import chart_title, section
from components.header import create_header

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
                    document.documentElement.style.backgroundColor = theme === 'dark' ? '#111110' : '#ffffff';
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
    Construct the main dashboard layout.
    """
    return html.Div(
        [
            # ── Header ────────────────────────────────────────────────────────
            create_header(
                title="Portfolio Overview",
                subtitle="Live P&L · Yahoo Finance · ASX ETFs",
                links_after=[
                    {"label": "Analytics", "href": "/analytics"},
                    {"label": "Intelligence", "href": "/intelligence"}
                ],
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

            # ── Live positions table ──────────────────────────────────────────
            section(
                html.Div([
                    chart_title("Live positions"),
                    
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
                        dmc.Button(
                            "Add Transaction",
                            id="compact-toggle-btn",
                            variant="subtle",
                            size="xs",
                            className="compact-toggle-btn",
                        ),
                    ], className="table-controls-row", style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"}),

                    dmc.Collapse(
                        html.Div(
                            [
                                html.Div(
                                    [
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
                                        ]),
                                        html.Div([
                                            html.P("Ticker", className="txn-label"),
                                            dmc.TextInput(
                                                id="txn-ticker",
                                                placeholder="e.g. VHY",
                                                className="txn-input-text",
                                            ),
                                        ]),
                                        html.Div([
                                            html.P("Shares", className="txn-label"),
                                            dmc.NumberInput(
                                                id="txn-shares",
                                                placeholder="0",
                                                min=0,
                                                className="txn-input-num",
                                            ),
                                        ]),
                                        html.Div([
                                            html.P("Price ($)", className="txn-label"),
                                            dmc.NumberInput(
                                                id="txn-price",
                                                placeholder="0.00",
                                                min=0,
                                                decimalScale=2,
                                                className="txn-input-num",
                                            ),
                                        ]),
                                        html.Div([
                                            html.P("Date", className="txn-label"),
                                            dmc.DateInput(
                                                id="txn-date",
                                                value=datetime.now().date(),
                                                valueFormat="YYYY-MM-DD",
                                                className="txn-input-date",
                                                allowDeselect=False,
                                            ),
                                        ]),
                                        html.Div([
                                            html.P("\u00a0", className="txn-label"),
                                            dmc.Button(
                                                "Submit",
                                                id="txn-submit",
                                                n_clicks=0,
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
                                html.P(f"Saved to: {CSV_PATH}", className="txn-path", style={"marginTop": "8px"}),
                            ],
                            className="txn-panel-inner-content",
                            style={"padding": "12px", "background": "var(--surface)", "borderRadius": "8px", "border": "1px solid var(--border)", "marginBottom": "16px"}
                        ),
                        id="txn-collapse",
                        opened=False,
                    ),
                ], style={"display": "flex", "flexDirection": "column"}),
                html.Div(id="live-table")
            ),

            # ── P&L history chart ─────────────────────────────────────────────
            section(
                html.Div([
                    chart_title("P&L from purchase date", "pnl-history"),
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
    )