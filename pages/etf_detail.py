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
                        html.A(
                            "← Portfolio",
                            href="/",
                            style={
                                "fontSize": "12px",
                                "color": "var(--t-sec)",
                                "textDecoration": "none",
                                "display": "inline-block",
                                "marginBottom": "8px",
                                "letterSpacing": "0.02em",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    ticker,
                                    style={
                                        "fontSize":      "22px",
                                        "fontWeight":    "600",
                                        "background":    "var(--surface)",
                                        "border":        "1px solid var(--border)",
                                        "borderRadius":  "6px",
                                        "padding":       "2px 10px",
                                        "marginRight":   "12px",
                                        "letterSpacing": "0.04em",
                                        "color":         "var(--t-pri)",
                                    },
                                ),
                                html.Span(
                                    name,
                                    style={
                                        "fontSize":   "18px",
                                        "fontWeight": "400",
                                        "color":      "var(--t-sec)",
                                    },
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center",
                                   "flexWrap": "wrap", "gap": "4px"},
                        ),
                    ]),
                    html.Div([
                        html.Div(id="etf-market-status", style={"marginBottom": "8px", "textAlign": "right"}),
                        html.Button(
                            "Refresh now", id="refresh-btn", n_clicks=0,
                            style={"fontWeight": "500", "fontSize": "12px", "padding": "4px 10px", "float": "right"},
                        ),
                    ]),
                ],
                style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "padding": "18px 24px 14px",
                    "borderBottom": "0.5px solid var(--border)",
                },
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
                            style={"display": "flex", "gap": "6px",
                                   "flexWrap": "wrap"},
                        ),
                    ],
                    style={
                        "display": "flex", "justifyContent": "space-between",
                        "alignItems": "center", "marginBottom": "10px",
                        "flexWrap": "wrap", "gap": "10px",
                    },
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
                html.Div(id="etf-position-cards",
                         style={"display": "flex", "gap": "10px",
                                "flexWrap": "wrap"}),
            ),

            # ── D. Transaction table ──────────────────────────────────────────
            section(
                chart_title("Transactions"),
                html.Div(id="etf-txn-table", style={"overflowX": "auto"}),
            ),

            # ── E. Dividend section ───────────────────────────────────────────
            html.Div(
                [
                    chart_title("Dividends"),
                    html.Div(id="etf-dividend-cards",
                             style={"display": "flex", "gap": "10px",
                                    "flexWrap": "wrap", "marginBottom": "16px"}),
                    dcc.Loading(
                        dcc.Graph(id="etf-dividend-chart",
                                  config={"displayModeBar": False},
                                  style={"height": "260px"}),
                        type="circle",
                        color=COLORS[1],
                    ),
                ],
                style={"padding": "20px 24px"},
            ),
        ],
        # Use CSS vars for the outer wrapper too
        style={
            "backgroundColor": "var(--bg)",
            "color":           "var(--t-pri)",
            "minHeight":       "100vh",
        },
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
                style={
                    "fontSize":       "12px",
                    "padding":        "3px 12px",
                    "borderRadius":   "20px",
                    "cursor":         "pointer",
                    "fontWeight":     "500",
                    # Active button gets a solid accent border; inactive is muted
                    "background":     COLORS[0] if is_active else "var(--surface)",
                    "border":         f"1px solid {COLORS[0]}" if is_active
                                      else "1px solid var(--border)",
                    "color":          "#ffffff" if is_active else "var(--t-pri)",
                },
            )
        )
    return buttons

