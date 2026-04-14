"""
pages/intelligence.py
======================
Portfolio Intelligence page.
Route: /intelligence

Sections
--------
A. Risk scorecard    — vol / Sharpe / max drawdown / current drawdown (4 cards)
B. Equity curve      — cumulative portfolio return since first data point
C. Drawdown curve    — rolling drawdown from rolling peak
D. Per-ticker vol    — horizontal bar showing annualised vol per ETF
E. Sector exposure   — horizontal bar (portfolio-weighted blend)
F. Geographic exposure — horizontal bar (portfolio-weighted blend)
G. Smart alerts      — rule-based intelligence cards

All data comes from the shared portfolio-store (already in app.layout).
"""

from __future__ import annotations
import math
import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html, register_page

from config.constants import (
    BG, SURFACE, BORDER, GREEN, RED, T_PRI, T_SEC, COLORS, PLOTLY_BASE
)
from services.intelligence import (
    compute_risk_metrics,
    sector_exposure,
    geo_exposure,
    compute_smart_alerts,
)

register_page(__name__, path="/intelligence", title="Portfolio Intelligence")

# ── Style tokens (CSS vars for theme-awareness) ───────────────────────────────
_SEC = {"padding": "20px 24px", "borderBottom": "0.5px solid var(--border)"}
_CARD = {
    "background": "var(--surface)", "borderRadius": "10px",
    "padding": "16px 20px", "flex": "1", "minWidth": "150px",
}
_CHART_BASE = dict(
    paper_bgcolor=BG, plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=36, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)

# Alert level → colour mapping
_LEVEL_COLOR = {
    "danger":  "#E24B4A",
    "warning": "#EF9F27",
    "info":    "#378ADD",
}
_LEVEL_BG = {
    "danger":  "rgba(226,75,74,0.08)",
    "warning": "rgba(239,159,39,0.08)",
    "info":    "rgba(55,138,221,0.08)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    children = [html.Span(text, style={"fontSize": "13px", "fontWeight": "500",
                                        "color": "var(--t-pri)"})]
    if tooltip:
        children.append(html.Span("i", title=tooltip, style={
            "display": "inline-flex", "alignItems": "center",
            "justifyContent": "center", "width": "16px", "height": "16px",
            "borderRadius": "50%", "background": "var(--surface)",
            "border": "1px solid var(--border)", "fontSize": "10px",
            "color": "var(--t-sec)", "cursor": "help", "marginLeft": "6px",
        }))
    return html.Div(children, style={"display": "inline-flex", "alignItems": "center",
                                      "marginBottom": "12px"})


# ── Layout ────────────────────────────────────────────────────────────────────

def layout() -> html.Div:
    return html.Div([
        # ── Nav bar ───────────────────────────────────────────────────────────
        html.Div([
            html.A("← Portfolio", href="/", style={
                "fontSize": "12px", "color": "var(--t-sec)",
                "textDecoration": "none", "letterSpacing": "0.02em",
            }),
            html.Span("Portfolio Intelligence",
                      style={"fontSize": "20px", "fontWeight": "500",
                             "color": "var(--t-pri)", "marginLeft": "16px"}),
            html.Span("Risk · Allocation · Smart alerts",
                      style={"fontSize": "12px", "color": "var(--t-sec)",
                             "marginLeft": "10px"}),
        ], style={
            "display": "flex", "alignItems": "center", "gap": "0",
            "padding": "18px 24px 14px",
            "borderBottom": "0.5px solid var(--border)",
        }),

        # ── Ticker info ───────────────────────────────────────────────────────
        html.Div([
            html.Div(id="intel-ticker-info",
                     style={"fontSize": "12px", "color": "var(--t-sec)",
                            "textAlign": "center", "padding": "8px 0"}),
        ], style={
            "borderBottom": "0.5px solid var(--border)",
        }),

        # ── A. Risk scorecard ─────────────────────────────────────────────────
        html.Div([
            _section_title(
                "Risk metrics",
                "Computed from the price history currently loaded. "
                "Adjust the chart period on the main dashboard to change the window."
            ),
            html.Div(id="intel-risk-cards",
                     style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}),
        ], style=_SEC),

        # ── B. Equity curve ───────────────────────────────────────────────────
        html.Div([
            _section_title(
                "Cumulative return",
                "Value-weighted portfolio return compounded daily. "
                "Starts at 0% on the first date all ETFs have data."
            ),
            dcc.Loading(
                dcc.Graph(id="intel-equity-chart", config={"displayModeBar": False}),
                type="circle", color=COLORS[0],
            ),
        ], style=_SEC),

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        html.Div([
            _section_title(
                "Drawdown",
                "Rolling percentage decline from the portfolio's rolling peak. "
                "Shows how far below the high-water mark the portfolio currently sits."
            ),
            dcc.Loading(
                dcc.Graph(id="intel-drawdown-chart", config={"displayModeBar": False}),
                type="circle", color=RED,
            ),
        ], style=_SEC),

        # ── D + E + F — Three-column allocation row ────────────────────────────
        html.Div([
            # Per-ticker volatility
            html.Div([
                _section_title(
                    "Volatility by ETF",
                    "Annualised standard deviation of daily returns for each ETF "
                    "over the loaded history period. Higher = more price swings."
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-vol-chart", config={"displayModeBar": False},
                              style={"height": "260px"}),
                    type="circle", color=COLORS[2],
                ),
            ], style={"flex": "1", "minWidth": "260px"}),

            # Sector exposure
            html.Div([
                _section_title(
                    "Sector exposure",
                    "Portfolio-weighted blend of each ETF's sector breakdown. "
                    "Known ETFs use curated data; unknown tickers assigned to 'Other'."
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-sector-chart",
                              config={"displayModeBar": False},
                              style={"height": "260px"}),
                    type="circle", color=COLORS[3],
                ),
            ], style={"flex": "1", "minWidth": "260px"}),

            # Geographic exposure
            html.Div([
                _section_title(
                    "Geographic exposure",
                    "Portfolio-weighted blend of each ETF's geographic breakdown. "
                    "Known ETFs use curated data; unknown tickers assigned to 'Other'."
                ),
                dcc.Loading(
                    dcc.Graph(id="intel-geo-chart",
                              config={"displayModeBar": False},
                              style={"height": "260px"}),
                    type="circle", color=COLORS[4],
                ),
            ], style={"flex": "1", "minWidth": "260px"}),
        ], style={
            "display": "flex", "gap": "14px", "flexWrap": "wrap",
            **_SEC,
        }),

        # ── G. Smart alerts ───────────────────────────────────────────────────
        html.Div([
            _section_title(
                "Smart alerts",
                "Rule-based insights from your current holdings, "
                "allocation weights, and risk metrics."
            ),
            html.Div(id="intel-alerts",
                     style={"display": "flex", "flexDirection": "column",
                            "gap": "8px"}),
        ], style={**_SEC, "borderBottom": "none"}),

    ], style={"backgroundColor": "var(--bg)", "color": "var(--t-pri)",
              "minHeight": "100vh"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app) -> None:

    @app.callback(
        Output("intel-risk-cards",     "children"),
        Output("intel-equity-chart",   "figure"),
        Output("intel-drawdown-chart", "figure"),
        Output("intel-vol-chart",      "figure"),
        Output("intel-sector-chart",   "figure"),
        Output("intel-geo-chart",      "figure"),
        Output("intel-alerts",         "children"),
        Output("intel-ticker-info",    "children"),
        Input("portfolio-store",       "data"),
        Input("live-interval",         "n_intervals"),
    )
    def update_intelligence(port_data, n_intervals):

        # ── Empty state ───────────────────────────────────────────────────────
        def empty_fig(msg="Waiting for portfolio data…"):
            f = go.Figure()
            f.update_layout(
                **_CHART_BASE, height=280,
                annotations=[dict(text=msg, showarrow=False,
                                  font=dict(color=T_SEC, size=13))],
            )
            return f

        no_data_cards = [_metric_card("—", "—")]
        no_data_alert = [_alert_card({
            "level": "info", "icon": "⏳",
            "title": "Waiting for data",
            "detail": "Portfolio data is still loading. Please wait.",
        })]

        if not port_data or "holdings" not in port_data or not port_data["holdings"]:
            return (no_data_cards,
                    empty_fig(), empty_fig(), empty_fig(), empty_fig(), empty_fig(),
                    no_data_alert)

        holdings  = port_data["holdings"]
        histories = port_data.get("histories", {})

        # ── A. Risk metrics ───────────────────────────────────────────────────
        metrics = compute_risk_metrics(port_data)

        def fmt(v, suffix="", prefix=""):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return "N/A"
            return f"{prefix}{v:+.2f}{suffix}" if suffix == "%" and v < 0 \
                else f"{prefix}{v:.2f}{suffix}"

        vol     = metrics["vol"]
        sharpe  = metrics["sharpe"]
        max_dd  = metrics["max_dd"]
        cur_dd  = metrics["current_dd"]
        n_days  = metrics["n_days"]

        # Colour logic
        vol_c    = RED if (vol or 0) > 20 else (COLORS[2] if (vol or 0) > 12 else GREEN)
        sharpe_c = GREEN if (sharpe or 0) > 1 else (COLORS[2] if (sharpe or 0) > 0.5 else RED)
        dd_c     = RED if (max_dd or 0) < -15 else (COLORS[2] if (max_dd or 0) < -8 else GREEN)
        cdd_c    = RED if (cur_dd or 0) < -10 else (COLORS[2] if (cur_dd or 0) < -5 else GREEN)

        risk_cards = [
            _metric_card("Annualised volatility",
                         "N/A" if vol is None or math.isnan(vol) else f"{vol:.1f}%",
                         f"over {n_days} trading days", vol_c),
            _metric_card("Sharpe ratio",
                         "N/A" if sharpe is None or math.isnan(sharpe) else f"{sharpe:.2f}",
                         f"Rf = {4.35:.2f}%  ·  {n_days}d", sharpe_c),
            _metric_card("Max drawdown",
                         "N/A" if max_dd is None or math.isnan(max_dd) else f"{max_dd:.1f}%",
                         "peak-to-trough", dd_c),
            _metric_card("Current drawdown",
                         "N/A" if cur_dd is None or math.isnan(cur_dd) else f"{cur_dd:.1f}%",
                         "from recent high", cdd_c),
        ]

        # ── B. Equity curve ───────────────────────────────────────────────────
        eq_fig = go.Figure()
        eq_fig.update_layout(
            **_CHART_BASE, height=300,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                       zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
            hovermode="x unified",
        )
        ret_dates  = metrics.get("ret_dates", [])
        ret_values = metrics.get("ret_values", [])
        if ret_dates and ret_values:
            last_val = ret_values[-1]
            line_color = GREEN if last_val >= 0 else RED
            fill_color = "rgba(29,158,117,0.12)" if last_val >= 0 \
                         else "rgba(226,75,74,0.10)"
            eq_fig.add_trace(go.Scatter(
                x=ret_dates, y=ret_values,
                mode="lines", name="Portfolio",
                fill="tozeroy", fillcolor=fill_color,
                line=dict(color=line_color, width=2),
                hovertemplate="%{y:.2f}%<extra></extra>",
            ))
            eq_fig.add_hline(y=0, line_color=BORDER, line_width=0.8)

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        dd_fig = go.Figure()
        dd_fig.update_layout(
            **_CHART_BASE, height=260,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                       zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
            hovermode="x unified",
        )
        dd_dates  = metrics.get("dd_dates", [])
        dd_values = metrics.get("dd_values", [])
        if dd_dates and dd_values:
            dd_fig.add_trace(go.Scatter(
                x=dd_dates, y=dd_values,
                mode="lines", name="Drawdown",
                fill="tozeroy",
                fillcolor="rgba(226,75,74,0.15)",
                line=dict(color=RED, width=1.5),
                hovertemplate="%{y:.2f}%<extra></extra>",
            ))
            dd_fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
            # Mark the max drawdown point
            if dd_values:
                min_val = min(dd_values)
                min_idx = dd_values.index(min_val)
                dd_fig.add_trace(go.Scatter(
                    x=[dd_dates[min_idx]], y=[min_val],
                    mode="markers+text",
                    marker=dict(color=RED, size=8, symbol="circle"),
                    text=[f"Max {min_val:.1f}%"],
                    textposition="top right",
                    textfont=dict(size=10, color=RED),
                    showlegend=False,
                    hoverinfo="skip",
                ))

        # ── D. Per-ticker volatility ──────────────────────────────────────────
        ticker_vols = metrics.get("ticker_vols", {})
        vol_fig = go.Figure()
        vol_fig.update_layout(
            **_CHART_BASE, height=260,
            xaxis=dict(gridcolor=BORDER, ticksuffix="%"),
            yaxis=dict(showgrid=False),
            hovermode="y unified",
        )
        if ticker_vols:
            tv_sorted = sorted(
                [(t, v) for t, v in ticker_vols.items()
                 if v is not None and not math.isnan(v)],
                key=lambda x: x[1],
            )
            tickers_sorted = [x[0] for x in tv_sorted]
            vols_sorted    = [x[1] for x in tv_sorted]
            bar_colors     = [RED if v > 20 else COLORS[2] if v > 12 else GREEN
                              for v in vols_sorted]
            vol_fig.add_trace(go.Bar(
                x=vols_sorted, y=tickers_sorted,
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.1f}%" for v in vols_sorted],
                textposition="outside",
                textfont=dict(size=11),
            ))

        # ── E. Sector exposure ────────────────────────────────────────────────
        sec_exp  = sector_exposure(port_data)
        sec_fig  = go.Figure()
        sec_fig.update_layout(
            **_CHART_BASE, height=260,
            xaxis=dict(gridcolor=BORDER, ticksuffix="%", range=[0, 105]),
            yaxis=dict(showgrid=False),
            hovermode="y unified",
        )
        if sec_exp:
            sec_sorted = sorted(sec_exp.items(), key=lambda x: x[1])
            labels = [x[0] for x in sec_sorted]
            vals   = [x[1] for x in sec_sorted]
            sec_fig.add_trace(go.Bar(
                x=vals, y=labels,
                orientation="h",
                marker_color=[
                    RED if v >= 40 else COLORS[2] if v >= 25 else COLORS[0]
                    for v in vals
                ],
                text=[f"{v:.1f}%" for v in vals],
                textposition="outside",
                textfont=dict(size=11),
            ))

        # ── F. Geographic exposure ────────────────────────────────────────────
        geo_exp_data = geo_exposure(port_data)
        geo_fig      = go.Figure()
        geo_fig.update_layout(
            **_CHART_BASE, height=260,
            xaxis=dict(gridcolor=BORDER, ticksuffix="%", range=[0, 115]),
            yaxis=dict(showgrid=False),
            hovermode="y unified",
        )
        if geo_exp_data:
            geo_sorted = sorted(geo_exp_data.items(), key=lambda x: x[1])
            g_labels   = [x[0] for x in geo_sorted]
            g_vals     = [x[1] for x in geo_sorted]
            geo_fig.add_trace(go.Bar(
                x=g_vals, y=g_labels,
                orientation="h",
                marker_color=[
                    RED if v >= 60 else COLORS[2] if v >= 40 else COLORS[4]
                    for v in g_vals
                ],
                text=[f"{v:.1f}%" for v in g_vals],
                textposition="outside",
                textfont=dict(size=11),
            ))

        # ── G. Smart alerts ───────────────────────────────────────────────────
        raw_alerts    = compute_smart_alerts(metrics, port_data)
        alert_cards   = [_alert_card(a) for a in raw_alerts]

        # ── Ticker info display ───────────────────────────────────────────────
        unique_tickers = list(set(h["ticker"] for h in holdings if "ticker" in h))
        ticker_info_text = f"Analyzing {len(unique_tickers)} tickers: {', '.join(sorted(unique_tickers))}"

        return (risk_cards, eq_fig, dd_fig, vol_fig,
                sec_fig, geo_fig, alert_cards, ticker_info_text)


def _alert_card(alert: dict) -> html.Div:
    """Render one smart alert as a styled card."""
    level  = alert.get("level", "info")
    color  = _LEVEL_COLOR.get(level, COLORS[0])
    bg     = _LEVEL_BG.get(level, "rgba(55,138,221,0.08)")
    return html.Div([
        html.Div([
            html.Span(alert.get("icon", "ℹ"),
                      style={"fontSize": "18px", "marginRight": "10px",
                             "lineHeight": "1"}),
            html.Div([
                html.Span(alert.get("title", ""),
                          style={"fontSize": "13px", "fontWeight": "500",
                                 "color": color}),
                html.Span(" — " + alert.get("detail", ""),
                          style={"fontSize": "12px", "color": "var(--t-sec)"}),
            ]),
        ], style={"display": "flex", "alignItems": "flex-start"}),
    ], style={
        "background":   bg,
        "border":       f"0.5px solid {color}",
        "borderRadius": "8px",
        "padding":      "12px 16px",
    })