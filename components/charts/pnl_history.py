"""
P&L History Chart Component.

Builds a line chart showing the portfolio's unrealised P&L over time,
with optional benchmark overlays.
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import GREEN, RED, COLORS
from core.engine.utils import get_period_cutoff
from components.charts.helpers import build_benchmark_traces

def build_pnl_history_figure(
    holdings: list[dict],
    mode: str,
    period: str,
    theme_tokens: dict,
    selected: str = "Portfolio",
) -> go.Figure:
    """
    Build a Plotly line chart for P&L history over a given period.

    Args:
        holdings: List of enriched holding dictionaries.
        mode: Display mode, either "abs" (absolute $) or "pct" (percentage).
        period: Time period to display (e.g., "1M", "YTD", "max").
        theme_tokens: Dictionary of UI theme colors and base layouts.
        selected: The ticker to highlight, or "Portfolio" for the aggregate.

    Returns:
        A Plotly go.Figure object.
    """
    BORDER      = theme_tokens["BORDER"]
    T_SEC       = theme_tokens["T_SEC"]
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
        **PLOTLY_BASE,
    )

    color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}
    cutoff    = get_period_cutoff(period)

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

        if mode == "pct":
            # For pct mode we show % return from the start of the selected window.
            # When a cutoff is active, cpnl at the cutoff date is already some
            # non-zero $ value (since the underlying buy dates precede the cutoff).
            # Re-zero it so the portfolio line and benchmark both start at 0%.
            pnl_at_start = float(cpnl.iloc[0]) if len(cpnl) else 0.0
            y = ((cpnl - pnl_at_start) / ccost * 100).round(2)
        else:
            y = cpnl.round(2)
        fig.update_xaxes(range=[cpnl.index.min(), cpnl.index.max()])
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
            for trace in build_benchmark_traces(period, theme_tokens=theme_tokens, portfolio_start=cpnl.index.min()):
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
                marker=dict(size=10, color=theme_tokens.get("WARNING", "#EF9F27"), symbol="diamond",
                            line=dict(width=1.5, color=theme_tokens["BG"])),
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

            if mode == "pct":
                pnl_at_start = float(pnl_s.iloc[0]) if len(pnl_s) else 0.0
                tr_y = ((pnl_s - pnl_at_start) / cost_s * 100).round(2)
            else:
                tr_y = pnl_s.round(2)
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
                marker=dict(size=10, color=theme_tokens.get("WARNING", "#EF9F27"), symbol="diamond",
                            line=dict(width=1.5, color=theme_tokens["BG"])),
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

            if mode == "pct":
                pnl_at_start = float(cpnl.iloc[0]) if len(cpnl) else 0.0
                y = ((cpnl - pnl_at_start) / ccost * 100).round(2)
            else:
                y = cpnl.round(2)
            fig.update_xaxes(range=[cpnl.index.min(), cpnl.index.max()])

            fig.add_trace(go.Scatter(
                x=cpnl.index, y=y,
                name=f"{selected} (combined)",
                mode="lines",
                fill="tozeroy",
                fillcolor=f"{theme_tokens.get('INFO', '#378ADD')}1A", # ~10% opacity
                line=dict(color=bc, width=2.5),
                hovertemplate=(
                    "%{y:.2f}%<extra>" + selected + " combined</extra>"
                    if mode == "pct"
                    else "$%{y:,.2f}<extra>" + selected + " combined</extra>"
                ),
            ))

            if mode == "pct":
                for trace in build_benchmark_traces(period, theme_tokens=theme_tokens, portfolio_start=cpnl.index.min()):
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
