"""
pages/intelligence.py
======================
Portfolio Intelligence page.
Route: /intelligence

UI fixes in this version
------------------------
1. Geo chart — now uses symbol-suffix region inference (fixed in
   services/intelligence.py); no change needed in page itself but
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
import math
import plotly.graph_objects as go
from dash import Input, Output, dcc, html, register_page

from config.constants import (
    BG, SURFACE, BORDER, GREEN, RED, T_PRI, T_SEC, COLORS
)
from services.intelligence import (
    compute_risk_metrics,
    sector_exposure,
    geo_exposure,
    compute_smart_alerts,
)

register_page(__name__, path="/intelligence", title="Portfolio Intelligence")

# ─────────────────────────────────────────────────────────────────────────────
# Style constants — all use CSS vars for theme compatibility
# ─────────────────────────────────────────────────────────────────────────────

# Every page section: equal padding + bottom border (matches portfolio page)
_SEC = {
    "padding":      "20px 24px",
    "borderBottom": "0.5px solid var(--border)",
}

# Stat card
_CARD = {
    "background":   "var(--surface)",
    "borderRadius": "10px",
    "padding":      "16px 20px",
    "flex":         "1",
    "minWidth":     "150px",
}

# Plotly base for line / area charts (tight margins, labels fit inside)
_LINE_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=24, t=36, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,  # Preserve zoom/pan state across auto-refreshes
)

# Plotly base for horizontal bar charts — wide left margin for y-axis labels
_BAR_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=12),
    margin=dict(l=110, r=60, t=16, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    showlegend=False,
    uirevision=True,  # Preserve state across auto-refreshes
)

# Alert level styling
_LEVEL_COLOR = {"danger": "#E24B4A", "warning": "#EF9F27", "info":  "#378ADD"}
_LEVEL_BG    = {
    "danger":  "rgba(226,75,74,0.08)",
    "warning": "rgba(239,159,39,0.08)",
    "info":    "rgba(55,138,221,0.08)",
}

# Bar chart row height formula
_BAR_ROW_PX = 36
_BAR_MIN_H  = 200


def _bar_height(n_rows: int) -> int:
    return max(_BAR_MIN_H, n_rows * _BAR_ROW_PX + 60)


# ─────────────────────────────────────────────────────────────────────────────
# Reusable UI helpers
# ─────────────────────────────────────────────────────────────────────────────

def _metric_card(label: str, value: str, sub: str | None = None,
                 color: str = "var(--t-pri)") -> html.Div:
    return html.Div([
        html.P(label, style={"fontSize": "11px", "color": "var(--t-sec)",
                              "margin": "0 0 4px"}),
        html.P(value, style={"fontSize": "22px", "fontWeight": "600",
                              "margin": "0", "color": color,
                              "letterSpacing": "-0.02em"}),
        html.P(sub, style={"fontSize": "11px", "color": "var(--t-sec)",
                            "margin": "3px 0 0"}) if sub else None,
    ], style=_CARD)


def _section_title(text: str, tooltip: str = "") -> html.Div:
    children = [
        html.Span(text, style={"fontSize": "13px", "fontWeight": "500",
                                "color": "var(--t-pri)"}),
    ]
    if tooltip:
        children.append(html.Span(
            "i", title=tooltip,
            style={
                "display":        "inline-flex",
                "alignItems":     "center",
                "justifyContent": "center",
                "width":          "16px",
                "height":         "16px",
                "borderRadius":   "50%",
                "background":     "var(--surface)",
                "border":         "1px solid var(--border)",
                "fontSize":       "10px",
                "color":          "var(--t-sec)",
                "cursor":         "help",
                "marginLeft":     "6px",
            },
        ))
    return html.Div(
        children,
        style={"display": "inline-flex", "alignItems": "center",
               "marginBottom": "12px"},
    )


def _alert_card(alert: dict) -> html.Div:
    level = alert.get("level", "info")
    color = _LEVEL_COLOR.get(level, COLORS[0])
    bg    = _LEVEL_BG.get(level, "rgba(55,138,221,0.08)")
    return html.Div(
        html.Div([
            html.Span(
                alert.get("icon", "ℹ"),
                style={"fontSize": "18px", "marginRight": "10px",
                       "lineHeight": "1", "flexShrink": "0"},
            ),
            html.Div([
                html.Span(
                    alert.get("title", ""),
                    style={"fontSize": "13px", "fontWeight": "500", "color": color},
                ),
                html.Span(
                    "  —  " + alert.get("detail", ""),
                    style={"fontSize": "12px", "color": "var(--t-sec)"},
                ),
            ]),
        ], style={"display": "flex", "alignItems": "flex-start"}),
        style={
            "background":   bg,
            "border":       f"0.5px solid {color}",
            "borderRadius": "8px",
            "padding":      "12px 16px",
        },
    )


def _empty_fig(msg: str = "Waiting for portfolio data…",
               height: int = 280,
               bar: bool = False) -> go.Figure:
    base = _BAR_BASE if bar else _LINE_BASE
    f = go.Figure()
    f.update_layout(
        **base, height=height,
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(color=T_SEC, size=13))],
    )
    return f


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
            html.Div(
                [
                    _section_title(
                        "Risk metrics",
                        "Computed from the price history window loaded on the "
                        "main dashboard. Widen the period to extend the window.",
                    ),
                    html.Div(
                        id="intel-risk-cards",
                        style={"display": "flex", "gap": "10px",
                               "flexWrap": "wrap"},
                    ),
                ],
                style=_SEC,
            ),

            # ── B. Equity curve ───────────────────────────────────────────────
            html.Div(
                [
                    _section_title(
                        "Cumulative return",
                        "Value-weighted portfolio return compounded daily. "
                        "Starts at 0% on the first date all ETFs have overlapping data.",
                    ),
                    dcc.Loading(
                        dcc.Graph(id="intel-equity-chart",
                                  config={"displayModeBar": False}),
                        type="circle", color=COLORS[0],
                    ),
                ],
                style=_SEC,
            ),

            # ── C. Drawdown curve ─────────────────────────────────────────────
            html.Div(
                [
                    _section_title(
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
                ],
                style=_SEC,
            ),

            # ── D · E · F  three-column bar charts ───────────────────────────
            html.Div(
                [
                    # D — Volatility per ETF
                    html.Div(
                        [
                            _section_title(
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
                            _section_title(
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
                            _section_title(
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
                    **_SEC,           # same padding + border as all other sections
                },
            ),

            # ── G. Smart alerts ───────────────────────────────────────────────
            html.Div(
                [
                    _section_title(
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
                style={**_SEC, "borderBottom": "none"},
            ),
        ],
        style={
            "backgroundColor": "var(--bg)",
            "color":           "var(--t-pri)",
            "minHeight":       "100vh",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app) -> None:

    @app.callback(
        Output("intel-risk-cards",     "children"),
        Output("intel-equity-chart",   "figure"),
        Output("intel-drawdown-chart", "figure"),
        Output("intel-vol-chart",      "figure"),
        Output("intel-sector-chart",   "figure"),
        Output("intel-geo-chart",      "figure"),
        Output("intel-alerts",         "children"),
        Output("intel-data-note",      "children"),
        Input("portfolio-store",       "data"),
    )
    def update_intelligence(port_data):

        # ── Empty / loading state ─────────────────────────────────────────────
        empty_bar = _empty_fig(height=_BAR_MIN_H, bar=True)
        no_data = (
            [_metric_card("—", "—")],
            _empty_fig(height=300),
            _empty_fig(height=260),
            empty_bar, empty_bar, empty_bar,
            [_alert_card({
                "level": "info", "icon": "⏳",
                "title": "Waiting for data",
                "detail": "Portfolio data is loading — please wait.",
            })],
            "Waiting for portfolio data…",
        )

        if not port_data or not port_data.get("holdings"):
            return no_data

        holdings  = port_data["holdings"]
        tickers   = sorted({h["ticker"] for h in holdings})
        fetched_at = port_data.get("fetched_at", "")

        data_note = (
            f"Analysing {len(tickers)} ETF(s): {', '.join(tickers)}"
            + (f"  ·  Prices updated {fetched_at}" if fetched_at else "")
            + "  ·  Sector & geo: live from Yahoo Finance (cached 24 h)"
        )

        # ── A. Risk metrics ───────────────────────────────────────────────────
        metrics = compute_risk_metrics(port_data)
        vol     = metrics["vol"]
        sharpe  = metrics["sharpe"]
        max_dd  = metrics["max_dd"]
        cur_dd  = metrics["current_dd"]
        n_days  = metrics["n_days"]

        def _nan(v):
            return v is None or (isinstance(v, float) and math.isnan(v))

        vol_c  = (RED    if not _nan(vol)    and vol    > 20
                  else COLORS[2] if not _nan(vol)    and vol    > 12 else GREEN)
        shr_c  = (GREEN  if not _nan(sharpe) and sharpe > 1
                  else COLORS[2] if not _nan(sharpe) and sharpe > 0.5 else RED)
        dd_c   = (RED    if not _nan(max_dd) and max_dd < -15
                  else COLORS[2] if not _nan(max_dd) and max_dd < -8 else GREEN)
        cdd_c  = (RED    if not _nan(cur_dd) and cur_dd < -10
                  else COLORS[2] if not _nan(cur_dd) and cur_dd < -5 else GREEN)

        risk_cards = [
            _metric_card(
                "Annualised volatility",
                f"{vol:.1f}%" if not _nan(vol) else "N/A",
                f"over {n_days} trading days", vol_c,
            ),
            _metric_card(
                "Sharpe ratio",
                f"{sharpe:.2f}" if not _nan(sharpe) else "N/A",
                f"Rf = 4.35 %  ·  {n_days} d window", shr_c,
            ),
            _metric_card(
                "Max drawdown",
                f"{max_dd:.1f}%" if not _nan(max_dd) else "N/A",
                "peak-to-trough", dd_c,
            ),
            _metric_card(
                "Current drawdown",
                f"{cur_dd:.1f}%" if not _nan(cur_dd) else "N/A",
                "from recent high", cdd_c,
            ),
        ]

        # ── B. Equity curve ───────────────────────────────────────────────────
        eq_fig = go.Figure()
        eq_fig.update_layout(
            **_LINE_BASE, height=300,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                       zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
            hovermode="x unified",
        )
        ret_dates  = metrics.get("ret_dates",  [])
        ret_values = metrics.get("ret_values", [])
        if ret_dates and ret_values:
            lv = ret_values[-1]
            eq_fig.add_trace(go.Scatter(
                x=ret_dates, y=ret_values,
                mode="lines", name="Portfolio",
                fill="tozeroy",
                fillcolor="rgba(29,158,117,0.12)" if lv >= 0
                          else "rgba(226,75,74,0.10)",
                line=dict(color=GREEN if lv >= 0 else RED, width=2),
                hovertemplate="%{y:.2f}%<extra></extra>",
            ))
            eq_fig.add_hline(y=0, line_color=BORDER, line_width=0.8)

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        dd_fig = go.Figure()
        dd_fig.update_layout(
            **_LINE_BASE, height=260,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                       zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
            hovermode="x unified",
        )
        dd_dates  = metrics.get("dd_dates",  [])
        dd_values = metrics.get("dd_values", [])
        if dd_dates and dd_values:
            dd_fig.add_trace(go.Scatter(
                x=dd_dates, y=dd_values,
                mode="lines", name="Drawdown",
                fill="tozeroy", fillcolor="rgba(226,75,74,0.15)",
                line=dict(color=RED, width=1.5),
                hovertemplate="%{y:.2f}%<extra></extra>",
            ))
            dd_fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
            # Annotate max drawdown point
            min_v   = min(dd_values)
            min_idx = dd_values.index(min_v)
            dd_fig.add_trace(go.Scatter(
                x=[dd_dates[min_idx]], y=[min_v],
                mode="markers+text",
                marker=dict(color=RED, size=8),
                text=[f"Max {min_v:.1f}%"],
                textposition="top right",
                textfont=dict(size=10, color=RED),
                showlegend=False, hoverinfo="skip",
            ))

        # ── D. Per-ticker volatility (horizontal bar) ─────────────────────────
        ticker_vols = metrics.get("ticker_vols", {})
        tv = sorted(
            [(t, v) for t, v in ticker_vols.items()
             if v is not None and not math.isnan(v)],
            key=lambda x: x[1],
        )
        vol_h = _bar_height(len(tv))
        vol_fig = go.Figure()
        vol_fig.update_layout(**_BAR_BASE, height=vol_h,
                              xaxis=dict(gridcolor=BORDER, ticksuffix="%"),
                              yaxis=dict(showgrid=False))
        if tv:
            vol_fig.add_trace(go.Bar(
                x=[v for _, v in tv],
                y=[t for t, _ in tv],
                orientation="h",
                marker_color=[
                    RED if v > 20 else COLORS[2] if v > 12 else GREEN
                    for _, v in tv
                ],
                text=[f"{v:.1f}%" for _, v in tv],
                textposition="outside",
                textfont=dict(size=11),
                cliponaxis=False,
            ))

        # ── E. Sector exposure (horizontal bar) ───────────────────────────────
        sec_exp = sector_exposure(port_data)
        sec_s   = sorted(sec_exp.items(), key=lambda x: x[1])
        sec_other = next((item for item in sec_s if item[0] == "Other"), None)
        if sec_other:
            sec_s.remove(sec_other)
            sec_s.insert(0, sec_other)
        sec_h   = _bar_height(len(sec_s))
        sec_fig = go.Figure()
        sec_fig.update_layout(
            **_BAR_BASE, height=sec_h,
            xaxis=dict(gridcolor=BORDER, ticksuffix="%", range=[0, 115]),
            yaxis=dict(showgrid=False),
        )
        if sec_s:
            sec_fig.add_trace(go.Bar(
                x=[v for _, v in sec_s],
                y=[k for k, _ in sec_s],
                orientation="h",
                marker_color=[
                    RED if v >= 40 else COLORS[2] if v >= 25 else COLORS[0]
                    for _, v in sec_s
                ],
                text=[f"{v:.1f}%" for _, v in sec_s],
                textposition="outside",
                textfont=dict(size=11),
                cliponaxis=False,
            ))

        # ── F. Geographic exposure (horizontal bar) ───────────────────────────
        geo_data = geo_exposure(port_data)
        geo_s    = sorted(geo_data.items(), key=lambda x: x[1])
        geo_other = next((item for item in geo_s if item[0] == "Other"), None)
        if geo_other:
            geo_s.remove(geo_other)
            geo_s.insert(0, geo_other)
        geo_h    = _bar_height(len(geo_s))
        geo_fig  = go.Figure()
        geo_fig.update_layout(
            **_BAR_BASE, height=geo_h,
            xaxis=dict(gridcolor=BORDER, ticksuffix="%", range=[0, 115]),
            yaxis=dict(showgrid=False),
        )
        if geo_s:
            geo_fig.add_trace(go.Bar(
                x=[v for _, v in geo_s],
                y=[k for k, _ in geo_s],
                orientation="h",
                marker_color=[
                    RED if v >= 60 else COLORS[2] if v >= 40 else COLORS[4]
                    for _, v in geo_s
                ],
                text=[f"{v:.1f}%" for _, v in geo_s],
                textposition="outside",
                textfont=dict(size=11),
                cliponaxis=False,
            ))

        # ── G. Smart alerts ───────────────────────────────────────────────────
        alert_cards = [_alert_card(a)
                       for a in compute_smart_alerts(metrics, port_data)]

        return (
            risk_cards,
            eq_fig, dd_fig,
            vol_fig, sec_fig, geo_fig,
            alert_cards,
            data_note,
        )