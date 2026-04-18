"""
components/charts.py
=====================
Pure chart functions — return go.Figure, accept plain Python data.

No Dash imports, no callbacks, no yfinance.
Pandas is used here (data transformation for charts), not in callbacks.

Exported functions
------------------
build_toggle_buttons(tickers, selected, theme_tokens)
build_pnl_history_figure(holdings, mode, theme_tokens, selected)
build_price_chart_figure(histories, theme_tokens)
build_allocation_figure(holdings, theme_tokens)
build_pnl_bar_figure(holdings, mode, theme_tokens)
build_day_pnl_figure(holdings, theme_tokens)
build_dividend_figure(holdings, theme_tokens)
build_corr_figure(histories, theme_tokens)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html

from config.constants import GREEN, RED, COLORS


# ─────────────────────────────────────────────────────────────────────────────
# Toggle buttons
# ─────────────────────────────────────────────────────────────────────────────

def build_toggle_buttons(
    holdings: list[dict],
    selected: str,
    theme_tokens: dict,
) -> list:
    """Return the list of html.Button elements for the P&L ticker selector."""
    T_PRI = theme_tokens["T_PRI"]
    tickers = ["Portfolio"] + [h["ticker"] for h in holdings]

    buttons = []
    for i, t in enumerate(tickers):
        is_active  = t == selected
        base_color = T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)]
        buttons.append(
            html.Button(
                t,
                id={"type": "ticker-btn", "index": t},
                n_clicks=0,
                style={
                    "fontSize":     "12px",
                    "padding":      "4px 12px",
                    "borderRadius": "20px",
                    "cursor":       "pointer",
                    "fontWeight":   "500",
                    "background":   base_color if is_active else "transparent",
                    "border":       f"1.5px solid {base_color}",
                    "color":        "#fff" if is_active else base_color,
                },
            )
        )
    return buttons


# ─────────────────────────────────────────────────────────────────────────────
# P&L history
# ─────────────────────────────────────────────────────────────────────────────

def _build_tranche_series(tr: dict):
    """Convert a tranche dict into (pnl_series, cost_series, buy_dt)."""
    idx        = pd.to_datetime(tr["dates"])
    pnl_series = pd.Series(tr["pnl"], index=idx)
    buy_dt     = pd.to_datetime(tr["buy_date"])
    pnl_series.loc[buy_dt] = 0
    pnl_series  = pnl_series.sort_index()
    cost_series = pd.Series(
        tr["shares"] * tr["buy_price"],
        index=pnl_series.index,
    )
    return pnl_series, cost_series, buy_dt


def build_pnl_history_figure(
    holdings: list[dict],
    mode: str,
    theme_tokens: dict,
    selected: str = "Portfolio",
) -> go.Figure:
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False, type="date"),
        yaxis=dict(
            gridcolor=BORDER,
            ticksuffix="%" if mode == "pct" else "",
            tickprefix="" if mode == "pct" else "$",
            zeroline=True,
            zerolinecolor=BORDER,
        ),
        hovermode="x unified",
        height=380,
        transition=dict(duration=500, easing="cubic-in-out"),
        **PLOTLY_BASE,
    )

    color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}

    if selected == "Portfolio":
        pnl_all, cost_all, purchase_pts = [], [], []

        for h in holdings:
            for tr in h.get("tranches", []):
                pnl_s, cost_s, buy_dt = _build_tranche_series(tr)
                pnl_all.append(pnl_s)
                cost_all.append(cost_s)
                purchase_pts.append((buy_dt, h["ticker"]))

        if pnl_all:
            all_pnl  = pd.concat(pnl_all,  axis=1).sort_index().ffill().fillna(0)
            all_cost = pd.concat(cost_all, axis=1).sort_index().ffill().fillna(0)
            cpnl     = all_pnl.sum(axis=1)
            ccost    = all_cost.sum(axis=1)
            y        = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)

            fig.add_trace(go.Scatter(
                x=cpnl.index, y=y,
                name="Portfolio", mode="lines",
                fill="tozeroy",
                fillcolor="rgba(29,158,117,0.12)" if y.iloc[-1] >= 0 else "rgba(226,75,74,0.10)",
                line=dict(color=GREEN if y.iloc[-1] >= 0 else RED, width=2.5),
            ))

            for dt, ticker in purchase_pts:
                fig.add_trace(go.Scatter(
                    x=[dt], y=[0], mode="markers",
                    marker=dict(size=10, color="#EF9F27", symbol="diamond",
                                line=dict(width=1.5, color="white")),
                    hovertemplate=f"{ticker} bought<br>{dt.date()}<extra></extra>",
                    showlegend=False,
                ))

    else:
        hm = next((h for h in holdings if h["ticker"] == selected), None)
        if hm:
            bc       = color_map.get(selected, COLORS[0])
            pnl_all  = []
            cost_all = []

            for tr in hm.get("tranches", []):
                pnl_s, cost_s, buy_dt = _build_tranche_series(tr)
                pnl_all.append(pnl_s)
                cost_all.append(cost_s)

                fig.add_trace(go.Scatter(
                    x=pnl_s.index,
                    y=(pnl_s / cost_s * 100).round(2) if mode == "pct" else pnl_s,
                    name=f"{tr['buy_date']} ({int(tr['shares'])} shares)",
                    mode="lines",
                    line=dict(color=bc, width=1, dash="dot"),
                    opacity=0.5,
                ))
                fig.add_trace(go.Scatter(
                    x=[buy_dt], y=[0], mode="markers",
                    marker=dict(size=10, color="#EF9F27", symbol="diamond"),
                    showlegend=False,
                ))

            if pnl_all:
                all_pnl  = pd.concat(pnl_all,  axis=1).sort_index().ffill().fillna(0)
                all_cost = pd.concat(cost_all, axis=1).sort_index().ffill().fillna(0)
                cpnl     = all_pnl.sum(axis=1)
                ccost    = all_cost.sum(axis=1)
                y        = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl

                fig.add_trace(go.Scatter(
                    x=cpnl.index, y=y,
                    name=f"{selected} (combined)",
                    mode="lines", fill="tozeroy",
                    fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=bc, width=2.5),
                ))

    fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Normalised price history
# ─────────────────────────────────────────────────────────────────────────────

def build_price_chart_figure(histories: dict, theme_tokens: dict) -> go.Figure:
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER),
        **PLOTLY_BASE,
    )

    for i, (t, recs) in enumerate(histories.items()):
        df = pd.DataFrame(recs)
        if df.empty or not df["Close"].iloc[0]:
            continue
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=(df["Close"] / df["Close"].iloc[0] * 100).round(2),
            name=t, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=1.8),
        ))

    fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Allocation donut
# ─────────────────────────────────────────────────────────────────────────────

def build_allocation_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    BG          = theme_tokens["BG"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    fig.add_trace(go.Pie(
        labels=[x["ticker"] for x in holdings],
        values=[x["mkt_value"] for x in holdings],
        hole=0.45,
        marker=dict(colors=COLORS[:len(holdings)], line=dict(color=BG, width=2)),
        textinfo="label+percent",
        textfont=dict(size=12),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Unrealised P&L bar
# ─────────────────────────────────────────────────────────────────────────────

def build_pnl_bar_figure(
    holdings: list[dict],
    mode: str,
    theme_tokens: dict,
) -> go.Figure:
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(
            gridcolor=BORDER,
            ticksuffix="%" if mode == "pct" else "",
            tickprefix="" if mode == "pct" else "$",
        ),
        **PLOTLY_BASE,
    )

    key = "pnl_pct" if mode == "pct" else "pnl"
    h   = sorted(holdings, key=lambda x: x[key])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x[key] for x in h],
        marker_color=[GREEN if x[key] >= 0 else RED for x in h],
        text=[
            f"{'+' if x[key] >= 0 else ''}{'%' if mode == 'pct' else '$'}{abs(x[key]):,.2f}"
            for x in h
        ],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Day P&L bar
# ─────────────────────────────────────────────────────────────────────────────

def build_day_pnl_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )

    h = sorted(holdings, key=lambda x: x["day_pnl"])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x["day_pnl"] for x in h],
        marker_color=[GREEN if x["day_pnl"] >= 0 else RED for x in h],
        text=[
            f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct'] >= 0 else ''}{x['day_chg_pct']:.2f}%"
            for x in h
        ],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Annual dividend bar
# ─────────────────────────────────────────────────────────────────────────────

def build_dividend_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    T_SEC       = theme_tokens["T_SEC"]
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )

    h = [x for x in holdings if x["annual_div"] > 0]
    if not h:
        fig.add_annotation(
            text="No dividend data yet — holdings are recent",
            showarrow=False, font=dict(color=T_SEC, size=13),
        )
        return fig

    h_s = sorted(h, key=lambda x: x["annual_div"], reverse=True)
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s],
        y=[x["annual_div"] for x in h_s],
        marker_color=COLORS[1],
        text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Correlation heatmap
# ─────────────────────────────────────────────────────────────────────────────

def build_corr_figure(histories: dict, theme_tokens: dict) -> go.Figure:
    T_SEC       = theme_tokens["T_SEC"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)

    if len(histories) < 2:
        fig.add_annotation(
            text="Need 2+ holdings with history",
            showarrow=False, font=dict(color=T_SEC, size=13),
        )
        return fig

    dfs = {}
    for t, r in histories.items():
        s = pd.DataFrame(r).set_index("Date")["Close"].pct_change().dropna()
        if len(s) >= 10:
            dfs[t] = s

    if len(dfs) < 2:
        fig.add_annotation(
            text="Need 2+ holdings with at least 10 days of history",
            showarrow=False, font=dict(color=T_SEC, size=13),
        )
        return fig

    corr  = pd.DataFrame(dfs).corr(min_periods=10).round(2)
    ticks = list(corr.columns)
    fig.add_trace(go.Heatmap(
        z=corr.values.tolist(), x=ticks, y=ticks,
        colorscale=[[0, "#1D9E75"], [0.5, "#EF9F27"], [1, "#E24B4A"]],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values.tolist()],
        texttemplate="%{text}", textfont=dict(size=11),
        showscale=True, colorbar=dict(thickness=12, len=0.8),
    ))
    fig.update_layout(
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11), autorange="reversed"),
    )
    return fig