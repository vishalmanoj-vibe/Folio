"""
callbacks/chart_callbacks.py
=============================
Chart callbacks.

Changes in this version
-----------------------
1. Benchmark overlay (S&P 500 and ASX 200) on the P&L history chart.
   - Only shown in % mode (dollar mode is meaningless for index comparison).
   - Each index is normalised to 0% at the start of the selected period window.
   - Fetched via services.market.fetcher.fetch_benchmarks() which caches 1 h.
   - Displayed as muted dashed/dotted lines so they don't overpower the portfolio.

2. Dividend fix is in fetcher.py — no chart changes needed for that.

3. Duplicate callback registrations removed (from previous session).
"""

import logging
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html

from config.constants import GREEN, RED, COLORS, get_theme

logger = logging.getLogger(__name__)

# Muted colours so benchmarks don't overpower portfolio lines
_BENCH_STYLES = {
    "S&P 500": {"color": "#6B8FCC", "dash": "dash"},
    "ASX 200": {"color": "#CC8F6B", "dash": "dot"},
}


def _period_cutoff(period: str) -> "pd.Timestamp | None":
    now = pd.Timestamp.now()
    mapping = {
        "1mo": now - timedelta(days=30),
        "3mo": now - timedelta(days=91),
        "6mo": now - timedelta(days=182),
        "1y":  now - timedelta(days=365),
        "2y":  now - timedelta(days=730),
        "max": None,
    }
    return mapping.get(period, None)


def _build_benchmark_traces(period: str) -> list:
    """
    Return Plotly Scatter traces for S&P 500 and ASX 200 normalised to
    % return from the start of the selected period window.
    Only called when mode == 'pct'.
    """
    try:
        from services.market.fetcher import fetch_benchmarks
        benchmarks = fetch_benchmarks(period="max")
    except Exception as exc:
        logger.warning("Could not load benchmarks: %s", exc)
        return []

    cutoff = _period_cutoff(period)
    traces = []

    for label, records in benchmarks.items():
        if not records:
            continue
        try:
            df = pd.DataFrame(records)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

            if cutoff is not None:
                df = df[df.index >= cutoff]

            if df.empty or len(df) < 2:
                continue

            base  = float(df["Close"].iloc[0])
            pct_s = ((df["Close"] - base) / base * 100).round(2)
            latest = float(pct_s.iloc[-1])
            sign   = "+" if latest >= 0 else ""
            style  = _BENCH_STYLES.get(label, {"color": "#888888", "dash": "dash"})

            traces.append(go.Scatter(
                x=pct_s.index.strftime("%Y-%m-%d").tolist(),
                y=pct_s.tolist(),
                name=f"{label} ({sign}{latest:.1f}%)",
                mode="lines",
                line=dict(color=style["color"], width=1.4, dash=style["dash"]),
                opacity=0.75,
                hovertemplate=f"%{{y:.2f}}%<extra>{label}</extra>",
            ))
        except Exception as exc:
            logger.warning("Benchmark trace failed for %s: %s", label, exc)

    return traces


def register_callbacks(app) -> None:

    # ── Ticker toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("ticker-toggle-btns", "children"),
        Input("portfolio-store",     "data"),
        Input("theme-store",         "data"),
    )
    def build_toggle_btns(data, theme):
        t_    = get_theme(theme or "dark")
        T_PRI = t_["T_PRI"]
        if not data or "holdings" not in data:
            return []
        tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
        return [
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
                    "background":   "transparent",
                    "border": (
                        f"1.5px solid {T_PRI}"
                        if t == "Portfolio"
                        else f"1.5px solid {COLORS[(i - 1) % len(COLORS)]}"
                    ),
                    "color": T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)],
                },
            )
            for i, t in enumerate(tickers)
        ]

    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("pnl-mode",           "value"),
        Input("period-picker",      "value"),
        Input("theme-store",        "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State({"type": "ticker-btn", "index": ALL}, "id"),
    )
    def pnl_history_chart(data, mode, period, theme, n_clicks_list, btn_ids):
        t_          = get_theme(theme or "dark")
        BORDER      = t_["BORDER"]
        T_SEC       = t_["T_SEC"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        period      = period or "max"

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
            **PLOTLY_BASE,
        )

        if not data or "holdings" not in data:
            return fig

        selected = "Portfolio"
        if n_clicks_list and any(n and n > 0 for n in n_clicks_list):
            last_idx = max(range(len(n_clicks_list)), key=lambda i: n_clicks_list[i] or 0)
            selected = btn_ids[last_idx]["index"]

        holdings  = data["holdings"]
        color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}
        cutoff    = _period_cutoff(period)

        def build_series(tr):
            idx        = pd.to_datetime(tr["dates"])
            pnl_series = pd.Series(tr["pnl"], index=idx)
            buy_dt     = pd.to_datetime(tr["buy_date"])
            if buy_dt not in pnl_series.index:
                pnl_series.loc[buy_dt] = 0.0
            pnl_series = pnl_series.sort_index()
            cost_series = pd.Series(tr["shares"] * tr["buy_price"], index=pnl_series.index)
            if cutoff is not None:
                effective   = max(cutoff, buy_dt)
                pnl_series  = pnl_series[pnl_series.index   >= effective]
                cost_series = cost_series[cost_series.index >= effective]
            return pnl_series, cost_series, buy_dt

        # ── Portfolio view ────────────────────────────────────────────────────
        if selected == "Portfolio":
            pnl_all, cost_all, purchase_pts = [], [], []

            for h in holdings:
                for tr in h.get("tranches", []):
                    pnl_s, cost_s, buy_dt = build_series(tr)
                    if pnl_s.empty:
                        continue
                    pnl_all.append(pnl_s)
                    cost_all.append(cost_s)
                    purchase_pts.append((buy_dt, h["ticker"], tr))

            if not pnl_all:
                return fig

            all_pnl  = pd.concat(pnl_all,  axis=1).sort_index().ffill().fillna(0)
            all_cost = pd.concat(cost_all, axis=1).sort_index().ffill().fillna(0)
            cpnl     = all_pnl.sum(axis=1)
            ccost    = all_cost.sum(axis=1)
            y        = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)
            lv       = float(y.iloc[-1]) if len(y) else 0

            fig.add_trace(go.Scatter(
                x=cpnl.index,
                y=y,
                name="Portfolio",
                mode="lines",
                fill="tozeroy",
                fillcolor="rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)",
                line=dict(color=GREEN if lv >= 0 else RED, width=2.5),
                hovertemplate=(
                    "%{y:.2f}%<extra>Portfolio</extra>"
                    if mode == "pct"
                    else "$%{y:,.2f}<extra>Portfolio</extra>"
                ),
            ))

            # ── Benchmark overlays — % mode only ─────────────────────────────
            if mode == "pct":
                for trace in _build_benchmark_traces(period):
                    fig.add_trace(trace)
                fig.add_annotation(
                    text="Benchmarks normalised to period start",
                    xref="paper", yref="paper",
                    x=1.0, y=1.02,
                    xanchor="right", yanchor="bottom",
                    showarrow=False,
                    font=dict(size=10, color=T_SEC),
                )

            # ── Buy markers ───────────────────────────────────────────────────
            for buy_dt, ticker, tr in purchase_pts:
                if buy_dt in y.index:
                    marker_y = float(y.loc[buy_dt])
                elif len(y) > 0:
                    pos      = y.index.get_indexer([buy_dt], method="nearest")[0]
                    marker_y = float(y.iloc[pos])
                else:
                    marker_y = 0.0

                cost_val = tr["shares"] * tr["buy_price"]
                tip = (
                    f"<b>{ticker}</b> — Buy<br>"
                    f"Date: {tr['buy_date']}<br>"
                    f"Shares: {tr['shares']:g}<br>"
                    f"Price: ${tr['buy_price']:,.4f}<br>"
                    f"Cost: ${cost_val:,.2f}<br>"
                    f"Portfolio P&L then: "
                    + (f"{marker_y:+.2f}%" if mode == "pct" else f"${marker_y:+,.2f}")
                    + "<extra></extra>"
                )
                fig.add_trace(go.Scatter(
                    x=[buy_dt], y=[marker_y], mode="markers",
                    marker=dict(size=10, color="#EF9F27", symbol="diamond",
                                line=dict(width=1.5, color="white")),
                    hovertemplate=tip, showlegend=False,
                ))

        # ── Individual ticker view ─────────────────────────────────────────────
        else:
            hm = next((h for h in holdings if h["ticker"] == selected), None)
            if not hm:
                return fig

            bc = color_map.get(selected, COLORS[0])
            pnl_all, cost_all = [], []

            for tr in hm.get("tranches", []):
                pnl_s, cost_s, buy_dt = build_series(tr)
                if pnl_s.empty:
                    continue
                pnl_all.append(pnl_s)
                cost_all.append(cost_s)

                tr_y = (pnl_s / cost_s * 100).round(2) if mode == "pct" else pnl_s.round(2)
                fig.add_trace(go.Scatter(
                    x=pnl_s.index, y=tr_y,
                    name=f"{tr['buy_date']} ({tr['shares']:g} sh)",
                    mode="lines",
                    line=dict(color=bc, width=1, dash="dot"),
                    opacity=0.5,
                    hovertemplate=(
                        "%{y:.2f}%<extra>" + tr["buy_date"] + "</extra>"
                        if mode == "pct"
                        else "$%{y:,.2f}<extra>" + tr["buy_date"] + "</extra>"
                    ),
                ))

                marker_y = (
                    float(tr_y.loc[buy_dt])
                    if buy_dt in tr_y.index
                    else (float(tr_y.iloc[0]) if len(tr_y) else 0.0)
                )
                cost_val = tr["shares"] * tr["buy_price"]
                fig.add_trace(go.Scatter(
                    x=[buy_dt], y=[marker_y], mode="markers",
                    marker=dict(size=10, color="#EF9F27", symbol="diamond",
                                line=dict(width=1.5, color="white")),
                    hovertemplate=(
                        f"<b>{selected}</b> — Buy<br>"
                        f"Date: {tr['buy_date']}<br>"
                        f"Shares: {tr['shares']:g}<br>"
                        f"Price: ${tr['buy_price']:,.4f}<br>"
                        f"Cost: ${cost_val:,.2f}<extra></extra>"
                    ),
                    showlegend=False,
                ))

            if pnl_all:
                all_pnl  = pd.concat(pnl_all,  axis=1).sort_index().ffill().fillna(0)
                all_cost = pd.concat(cost_all, axis=1).sort_index().ffill().fillna(0)
                cpnl     = all_pnl.sum(axis=1)
                ccost    = all_cost.sum(axis=1)
                y        = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)

                fig.add_trace(go.Scatter(
                    x=cpnl.index, y=y,
                    name=f"{selected} (combined)",
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=bc, width=2.5),
                    hovertemplate=(
                        "%{y:.2f}%<extra>" + selected + " combined</extra>"
                        if mode == "pct"
                        else "$%{y:,.2f}<extra>" + selected + " combined</extra>"
                    ),
                ))

                if mode == "pct":
                    for trace in _build_benchmark_traces(period):
                        fig.add_trace(trace)
                    fig.add_annotation(
                        text="Benchmarks normalised to period start",
                        xref="paper", yref="paper",
                        x=1.0, y=1.02,
                        xanchor="right", yanchor="bottom",
                        showarrow=False,
                        font=dict(size=10, color=T_SEC),
                    )

        fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
        return fig

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, theme):
        t_          = get_theme(theme or "dark")
        BORDER      = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BORDER), **PLOTLY_BASE)
        if not data or "histories" not in data:
            return fig
        for i, (t, recs) in enumerate(data["histories"].items()):
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

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, theme):
        t_          = get_theme(theme or "dark")
        BG          = t_["BG"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "holdings" not in data:
            return fig
        h = data["holdings"]
        fig.add_trace(go.Pie(
            labels=[x["ticker"] for x in h],
            values=[x["mkt_value"] for x in h],
            hole=0.45,
            marker=dict(colors=COLORS[:len(h)], line=dict(color=BG, width=2)),
            textinfo="label+percent",
            textfont=dict(size=12),
        ))
        return fig

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, theme):
        t_          = get_theme(theme or "dark")
        BORDER      = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER,
                       ticksuffix="%" if mode == "pct" else "",
                       tickprefix="" if mode == "pct" else "$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        key = "pnl_pct" if mode == "pct" else "pnl"
        h   = sorted(data["holdings"], key=lambda x: x[key])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x[key] for x in h],
            marker_color=[GREEN if x[key] >= 0 else RED for x in h],
            text=[
                f"{'+' if x[key]>=0 else ''}{'%' if mode=='pct' else '$'}{abs(x[key]):,.2f}"
                for x in h
            ],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, theme):
        t_          = get_theme(theme or "dark")
        BORDER      = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = sorted(data["holdings"], key=lambda x: x["day_pnl"])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x["day_pnl"] for x in h],
            marker_color=[GREEN if x["day_pnl"] >= 0 else RED for x in h],
            text=[
                f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct']>=0 else ''}{x['day_chg_pct']:.2f}%"
                for x in h
            ],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Annual dividend income ────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart", "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, theme):
        t_          = get_theme(theme or "dark")
        T_SEC       = t_["T_SEC"]
        BORDER      = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = [x for x in data["holdings"] if x["annual_div"] > 0]
        if not h:
            fig.add_annotation(text="No dividend data yet — holdings are recent",
                               showarrow=False, font=dict(color=T_SEC, size=13))
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

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def corr_chart(data, theme):
        t_          = get_theme(theme or "dark")
        T_SEC       = t_["T_SEC"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]
        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "histories" not in data or len(data["histories"]) < 2:
            fig.add_annotation(text="Need 2+ holdings with history",
                               showarrow=False, font=dict(color=T_SEC, size=13))
            return fig
        dfs = {}
        for t, r in data["histories"].items():
            s = pd.DataFrame(r).set_index("Date")["Close"].pct_change().dropna()
            if len(s) >= 10:
                dfs[t] = s
        if len(dfs) < 2:
            fig.add_annotation(text="Need 2+ holdings with at least 10 days of history",
                               showarrow=False, font=dict(color=T_SEC, size=13))
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