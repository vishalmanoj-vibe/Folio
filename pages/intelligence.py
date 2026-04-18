"""
pages/intelligence.py
======================
Portfolio Intelligence page.
Route: /intelligence

UI fixes in this version
------------------------
1. Geo chart — now uses symbol-suffix region inference (fixed in
   services/intelligence_service.py); no change needed in page itself but
   layout is rebuilt to match the corrected data.

2. Bar chart label clipping — horizontal bar charts (vol, sector, geo)
   now use _BAR_BASE with l=110 left margin so labels like
   "Consumer Staples" or "South Korea" are fully visible.

3. CSS height conflict removed — dcc.Graph wrappers no longer have
   style={"height": "Xpx"}. Plotly's figure.layout.height controls
   canvas size exclusively; CSS height clips the canvas.

4. Uniform section structure — every section uses the same _SEC token
   (padding 20px 24px + bottom border). The three-column row (D/E/F)
   is wrapped in its own _SEC div, and each column has no extra padding
   so spacing is consistent with sections A–C and G.

5. Consistent chart heights — line charts (B, C) use fixed 300/260 px.
   Bar charts (D, E, F) scale to row count with a shared 36px-per-row
   formula and a 280 px minimum, all using autosize=False so Plotly
   respects the height value.
"""

from __future__ import annotations
from dash import dcc, html, register_page

from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC
)
from components.ui_helpers import section, chart_title

register_page(__name__, path="/intelligence", title="Portfolio Intelligence")


# ─────────────────────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────────────────────

def layout() -> html.Div:
    return html.Div(
        [
            # ── Nav header ────────────────────────────────────────────────────
            html.Div(
                [
                    html.A("← Portfolio", href="/", style={
                        "fontSize":      "12px",
                        "color":         "var(--t-sec)",
                        "textDecoration":"none",
                        "letterSpacing": "0.02em",
                    }),
                    html.Span(
                        "Portfolio Intelligence",
                        style={"fontSize": "20px", "fontWeight": "500",
                               "color": "var(--t-pri)", "marginLeft": "16px"},
                    ),
                    html.Span(
                        "Risk · Allocation · Smart alerts",
                        style={"fontSize": "12px", "color": "var(--t-sec)",
                               "marginLeft": "10px", "flex": "1"},
                    ),
                    html.Button(
                        "Refresh now", id="refresh-btn", n_clicks=0,
                        style={"fontWeight": "500", "fontSize": "12px", "padding": "4px 10px"},
                    ),
                ],
                style={
                    "display": "flex", "alignItems": "center",
                    "padding": "18px 24px 14px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── Data source note ──────────────────────────────────────────────
            html.Div(
                id="intel-data-note",
                style={
                    "padding":       "8px 24px",
                    "borderBottom":  "0.5px solid var(--border)",
                    "fontSize":      "12px",
                    "color":         "var(--t-sec)",
                    "minHeight":     "32px",
                },
            ),

            # ── A. Risk scorecard ─────────────────────────────────────────────
            section(
                chart_title(
                    "Risk metrics",
                    "Computed from the price history window loaded on the "
                    "main dashboard. Widen the period to extend the window.",
                ),
                html.Div(
                    id="intel-risk-cards",
                    style={"display": "flex", "gap": "10px",
                           "flexWrap": "wrap"},
                ),
            ),

            # ── B. Equity curve ───────────────────────────────────────────────
            section(
                chart_title(
                    "Cumulative return",
                    "Value-weighted portfolio return compounded daily. "
                    "Starts at 0% on the first date all ETFs have overlapping data.",
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-equity-chart",
                              config={"displayModeBar": False}),
                    type="circle", color=COLORS[0],
                ),
            ),

            # ── C. Drawdown curve ─────────────────────────────────────────────
            section(
                chart_title(
                    "Drawdown",
                    "Rolling % decline from the portfolio's rolling peak. "
                    "The worst point is annotated. Current drawdown is in "
                    "the Risk metrics scorecard above.",
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-drawdown-chart",
                              config={"displayModeBar": False}),
                    type="circle", color=RED,
                ),
            ),

            # ── D · E · F  three-column bar charts ───────────────────────────
            html.Div(
                [
                    # D — Volatility per ETF
                    html.Div(
                        [
                            chart_title(
                                "Volatility by ETF",
                                "Annualised std of daily returns per ETF over "
                                "the loaded history window. "
                                "Green < 12 % · Amber 12–20 % · Red > 20 %.",
                            ),
                            dcc.Loading(
                                # No style= height — Plotly controls canvas size
                                dcc.Graph(id="intel-vol-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[2],
                            ),
                        ],
                        style={"flex": "1", "minWidth": "260px"},
                    ),

                    # E — Sector exposure
                    html.Div(
                        [
                            chart_title(
                                "Sector exposure",
                                "Portfolio-weighted sector blend fetched live "
                                "from Yahoo Finance funds_data. Cached 24 h. "
                                "Red ≥ 40 % · Amber ≥ 25 % · Blue below.",
                            ),
                            dcc.Loading(
                                dcc.Graph(id="intel-sector-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[3],
                            ),
                        ],
                        style={"flex": "1", "minWidth": "260px"},
                    ),

                    # F — Geographic exposure
                    html.Div(
                        [
                            chart_title(
                                "Geographic exposure",
                                "Region inferred from each top-holding's "
                                "exchange suffix (e.g. .HK → Hong Kong, "
                                "no suffix → USA). Cached 24 h.",
                            ),
                            dcc.Loading(
                                dcc.Graph(id="intel-geo-chart",
                                          config={"displayModeBar": False}),
                                type="circle", color=COLORS[4],
                            ),
                        ],
                        style={"flex": "1", "minWidth": "260px"},
                    ),
                ],
                style={
                    "display":  "flex",
                    "gap":      "14px",
                    "flexWrap": "wrap",
                    "padding": "20px 24px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── G. Smart alerts ───────────────────────────────────────────────
            html.Div(
                [
                    chart_title(
                        "Smart alerts",
                        "Rule-based insights from holdings, allocation weights, "
                        "and risk metrics.",
                    ),
                    html.Div(
                        id="intel-alerts",
                        style={"display": "flex", "flexDirection": "column",
                               "gap": "8px"},
                    ),
                ],
                style={"padding": "20px 24px"},
            ),
        ],
        style={
            "backgroundColor": "var(--bg)",
            "color":           "var(--t-pri)",
            "minHeight":       "100vh",
        },
    )

# Callbacks are now located in callbacks/intelligence_callbacks.py