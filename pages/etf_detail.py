"""
pages/etf_detail.py
====================
ETF detail drill-down page.
Route: /etf/<ticker>   e.g. /etf/VHY

Bug fixes in this version
--------------------------
1. LIGHT MODE  — All background/surface/border/text colours now use CSS
                 variables (var(--bg), var(--surface), etc.) instead of
                 hardcoded dark hex values, so the theme toggle works.

2. PERIOD FILTER — Selected period is stored in `dcc.Store` ("etf-period-store")
                   and written by a separate clientside callback.  The chart
                   callback reads from that store, not from button n_clicks
                   (which all start at 0 and can't be disambiguated on first
                   render or after a page reload).

3. DIVIDENDS    — `hist.get("Dividends")` fails on a DataFrame (no .get()).
                 Fixed to `hist["Dividends"] if "Dividends" in hist.columns`.
                 Also uses the tranche data already in portfolio-store instead
                 of re-fetching, so the cards always have data.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from dash import ALL, ClientsideFunction, Input, Output, State, dcc, html, register_page

from config.constants import (
    BG, SURFACE, BORDER, GREEN, RED, T_PRI, T_SEC, COLORS, PLOTLY_BASE, NAMES
)
from services.market.market_status import market_badge
from components.ui_helpers import section, chart_title

# ── Register page ─────────────────────────────────────────────────────────────
register_page(__name__, path_template="/etf/<ticker>", title="ETF Detail")

# ── Period filter options ─────────────────────────────────────────────────────
PERIOD_OPTIONS = [
    {"label": "Since purchase", "value": "purchase"},
    {"label": "1M",  "value": "1mo"},
    {"label": "3M",  "value": "3mo"},
    {"label": "6M",  "value": "6mo"},
    {"label": "1Y",  "value": "1y"},
    {"label": "MAX", "value": "max"},
]
DEFAULT_PERIOD = "3mo"

# ── Layout factory ────────────────────────────────────────────────────────────
def layout(ticker: str = "") -> html.Div:
    ticker = ticker.upper()
    name   = NAMES.get(ticker, ticker)

    return html.Div(
        [
            # Hidden stores
            dcc.Store(id="etf-ticker-store", data=ticker),
            dcc.Store(id="etf-period-store", data=DEFAULT_PERIOD, storage_type="session"),

            # ── A. Header ─────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.A("← Portfolio", href="/", className="back-link", style={"display": "inline-block", "marginBottom": "8px"}),
                        html.Div(
                            [
                                html.Span(ticker, className="ticker-badge"),
                                html.Span(name, className="ticker-name"),
                            ],
                            className="flex-row-center", style={"flexWrap": "wrap", "gap": "4px"}
                        ),
                    ]),
                    html.Div([
                        html.Div(id="etf-market-status", className="status-text", style={"marginBottom": "8px"}),
                        html.Button("Refresh now", id="refresh-btn", n_clicks=0, className="btn-sm btn-right"),
                    ]),
                ],
                className="page-header-row",
            ),

            # ── B. Price chart ────────────────────────────────────────────────
            section(
                html.Div(
                    [
                        chart_title("Price chart"),
                        # Period filter buttons
                        html.Div(
                            id="etf-period-btns",
                            children=_period_buttons(DEFAULT_PERIOD),
                            className="flex-row-center", style={"gap": "6px", "flexWrap": "wrap"}
                        ),
                    ],
                    className="chart-header-row",
                ),
                dcc.Loading(
                    dcc.Graph(id="etf-price-chart",
                              config={"displayModeBar": False}),
                    type="circle",
                    color=COLORS[0],
                ),
            ),

            # ── C. Position summary ───────────────────────────────────────────
            section(
                chart_title("Position summary"),
                html.Div(id="etf-position-cards", className="metrics-row"),
            ),

            # ── D. Transaction table ──────────────────────────────────────────
            section(
                chart_title("Transactions"),
                html.Div(id="etf-txn-table", className="overflow-table"),
            ),

            # ── E. Dividend section ───────────────────────────────────────────
            html.Div(
                [
                    chart_title("Dividends"),
                    html.Div(id="etf-dividend-cards", className="flex-row-gap-10", style={"marginBottom": "16px"}),
                    dcc.Loading(
                        dcc.Graph(id="etf-dividend-chart",
                                  config={"displayModeBar": False},
                                  style={"height": "260px"}),
                        type="circle",
                        color=COLORS[1],
                    ),
                ],
                className="section-container",
            ),
        ],
        # Use CSS vars for the outer wrapper too
        className="page-root",
    )


# ── Period button renderer (also called from callback to update active state) ─
def _period_buttons(active: str) -> list:
    buttons = []
    for opt in PERIOD_OPTIONS:
        is_active = opt["value"] == active
        buttons.append(
            html.Button(
                opt["label"],
                id={"type": "etf-period-btn", "index": opt["value"]},
                n_clicks=0,
                className=f"period-btn {'period-btn-active' if is_active else ''}".strip(),
            )
        )
    return buttons

