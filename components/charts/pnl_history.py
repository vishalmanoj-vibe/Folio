# components/charts/pnl_history.py
"""
P&L History Chart Component.

Builds a line chart showing the portfolio's unrealised P&L over time,
with optional benchmark overlays.
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import GREEN, RED, COLORS
from core.engine.utils import get_period_cutoff
from components.charts.helpers import build_benchmark_traces, hex_to_rgba

def _build_intraday_figure(
    fig: "go.Figure",
    holdings: list[dict],
    mode: str,
    theme_tokens: dict,
) -> "go.Figure":
    """
    Build the 'Today' intraday P&L chart.

    Data source : session_cache JSON file (direct read) — bypasses the dcc.Store
                  entirely so stale max-period tranche data never causes an empty chart.
    Zero line   : prev_close from the enriched holding (yesterday's close via yfinance).
    Window      : ASX session 10:00–16:15 Sydney wall-clock.
    X-axis ticks: every 30 minutes.
    Updates     : every live-interval tick appends a new snapshot to the cache file.
    """
    import json as _json, os as _os
    from datetime import datetime as _dt

    BORDER  = theme_tokens["BORDER"]
    T_SEC   = theme_tokens["T_SEC"]
    GREEN_C = theme_tokens.get("GREEN", "#1D9E75")
    RED_C   = theme_tokens.get("RED",   "#E24B4A")

    now_syd      = pd.Timestamp.now(tz="Australia/Sydney")
    today_str    = now_syd.strftime("%Y-%m-%d")
    market_open  = pd.Timestamp(f"{today_str} 10:00:00", tz="Australia/Sydney")
    market_close = pd.Timestamp(f"{today_str} 16:15:00", tz="Australia/Sydney")

    # ── Load session cache directly from disk ─────────────────────────────────
    cache_path = _os.path.join("data", "cache", f"intraday_{today_str}.json")
    session_data: dict = {}
    try:
        if _os.path.exists(cache_path):
            with open(cache_path) as _f:
                session_data = _json.load(_f)
    except Exception:
        pass

    if not session_data:
        fig.add_annotation(
            text="Waiting for market session data (ASX opens 10:00 Sydney Time) …",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color=T_SEC),
        )
        return fig

    # Build a lookup: ticker -> prev_close from the enriched holdings in the store.
    # prev_close is always up-to-date regardless of which period was used for the store.
    prev_close_map  = {h["ticker"]: h.get("prev_close", 0.0) for h in holdings}
    total_shares_map = {h["ticker"]: h.get("total_shares", 0.0) for h in holdings}

    # ── Compute day P&L series per holding ────────────────────────────────────
    all_series: list[pd.Series] = []

    for ticker, points in session_data.items():
        prev_close   = prev_close_map.get(ticker, 0.0)
        total_shares = total_shares_map.get(ticker, 0.0)
        if prev_close <= 0 or total_shares <= 0 or not points:
            continue

        df = pd.DataFrame(points)
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize("Australia/Sydney")
        df = df.sort_values("Date").drop_duplicates("Date")
        df = df[(df["Date"] >= market_open) & (df["Date"] <= market_close)]

        if df.empty:
            continue

        price_s = df.set_index("Date")["Close"]
        
        # ── Data Sanitization ─────────────────────────────────────────────────
        # Filter out spurious zero-prices and forward-fill gaps to prevent 
        # sudden "cliff" drops in the chart during session gaps.
        price_s = price_s[price_s > 0].ffill()

        if price_s.empty:
            continue

        if mode == "pct":
            day_s = ((price_s - prev_close) / prev_close * 100).round(4)
        else:
            day_s = ((price_s - prev_close) * total_shares).round(2)

        # ── Anchor at 10:00 AM ────────────────────────────────────────────────
        # If the series doesn't start exactly at 10:00 AM, we prepend a zero point
        # to ensure the chart line starts at the y=0 axis for all tickers.
        if market_open not in day_s.index:
            day_s.loc[market_open] = 0.0
            day_s = day_s.sort_index()

        all_series.append(day_s)

    if not all_series:
        fig.add_annotation(
            text="Intraday data unavailable for this selection",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color=T_SEC),
        )
        return fig

    # ── Portfolio aggregate ───────────────────────────────────────────────────
    # Use ffill to propagate last known price. Fillna(0) for the start of day 
    # where some tickers might not have traded yet.
    combined = pd.concat(all_series, axis=1, sort=True).sort_index().ffill().fillna(0)

    if mode == "pct":
        # Weight by cost basis so larger positions contribute more
        weights = []
        for h in holdings:
            if h["ticker"] in session_data and h.get("prev_close", 0) > 0:
                weights.append(h.get("total_cost", h.get("prev_close", 1) * h.get("total_shares", 1)))
        if weights and len(weights) == combined.shape[1]:
            total_w    = sum(weights)
            weight_arr = [w / total_w for w in weights]
            portfolio_s = (combined * weight_arr).sum(axis=1).round(4)
        else:
            portfolio_s = combined.mean(axis=1).round(4)
    else:
        portfolio_s = combined.sum(axis=1).round(2)

    last_val   = float(portfolio_s.iloc[-1]) if len(portfolio_s) else 0.0
    line_color = GREEN_C if last_val >= 0 else RED_C
    fill_color = "rgba(29,158,117,0.12)" if last_val >= 0 else "rgba(226,75,74,0.10)"

    fig.add_trace(go.Scatter(
        x=portfolio_s.index,
        y=portfolio_s.values,
        name="Portfolio Today",
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=fill_color,
        line=dict(color=line_color, width=2.5),
        marker=dict(size=5, color=line_color),
        hovertemplate=(
            "<b>%{x|%H:%M}</b><br>"
            + ("%{y:+.2f}%<extra>Day change</extra>" if mode == "pct"
               else "$%{y:+,.2f}<extra>Day P&L</extra>")
        ),
    ))

    fig.add_hline(y=0, line_color=BORDER, line_width=0.8)

    # Corner annotation with latest value
    sign  = "+" if last_val >= 0 else ""
    label = f"{sign}{last_val:.2f}%" if mode == "pct" else f"{sign}${last_val:,.2f}"
    fig.add_annotation(
        text=f"<b>{label}</b>",
        xref="paper", yref="paper",
        x=0.01, y=0.97,
        xanchor="left", yanchor="top",
        showarrow=False,
        font=dict(size=14, color=line_color),
        bgcolor=theme_tokens.get("BG", "#1A1A2E"),
        borderpad=4,
    )

    return fig


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

    # Merge theme base with local overrides
    layout = PLOTLY_BASE.copy()
    layout.update(dict(
        xaxis=dict(
            showgrid=False, type="date",
            showspikes=True, spikecolor=T_SEC, spikethickness=1, spikedash="dash",
            tickfont=dict(size=10, color=T_SEC),
            automargin=True,
        ),
        yaxis=dict(
            gridcolor=BORDER,
            ticksuffix="%" if mode == "pct" else "",
            tickprefix="" if mode == "pct" else "$",
            zeroline=True,
            zerolinecolor=BORDER,
            tickfont=dict(size=11, color=T_SEC),
            automargin=True,
        ),
        hovermode="x unified",
        height=380,
        showlegend=False,
        margin=dict(t=30, b=30, l=60, r=20),
    ))
    
    fig = go.Figure()
    
    # ── Intraday vs Historical Axis Tuning ────────────────────────────────────
    if period == "1d":
        layout["xaxis"].update(dict(
            tickformat="%H:%M",
            dtick=30 * 60 * 1000,  # 30-minute ticks in milliseconds
            tickangle=0,
        ))
        # Fix x-axis to ASX session window 10:00–16:15 Sydney wall-clock
        now_syd   = pd.Timestamp.now(tz="Australia/Sydney")
        today_str = now_syd.strftime("%Y-%m-%d")
        # Use ISO format with timezone offset to ensure Plotly respects Sydney time
        range_start = f"{today_str}T10:00:00"
        range_end   = f"{today_str}T16:15:00"
        layout["xaxis"].update(dict(
            range=[range_start, range_end],
        ))
    else:
        layout["xaxis"].update(dict(
            tickformat=None,
        ))

    fig.update_layout(layout)

    color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}
    cutoff    = get_period_cutoff(period)

    # ── Intraday 'Today' chart — dedicated rendering path ────────────────────
    if period == "1d":
        return _build_intraday_figure(fig, holdings, mode, theme_tokens)

    def build_series(tr):
        idx        = pd.to_datetime(tr["dates"])
        pnl_series = pd.Series(tr["pnl"], index=idx)
        buy_dt     = pd.to_datetime(tr["buy_date"])
        # Only inject a zero-value anchor at buy_dt for historical (daily) periods.
        # For intraday ("1d") the buy date is always in the past, so injecting it
        # would add an out-of-window point that distorts the series after sorting.
        if period != "1d" and buy_dt not in pnl_series.index:
            pnl_series.loc[buy_dt] = 0.0
        pnl_series = pnl_series.sort_index()
        cost_series = pd.Series(tr["shares"] * tr["buy_price"], index=pnl_series.index)
        if cutoff is not None:
            effective   = max(cutoff, buy_dt) if period != "1d" else cutoff
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
            
        y = y.round(2)
        lv = float(y.iloc[-1]) if len(y) else 0

        fig.add_trace(go.Scatter(
            x=cpnl.index,
            y=y,
            name="Portfolio",
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)",
            line=dict(color=GREEN if lv >= 0 else RED, width=2.5),
            hovertemplate=(
                "%{y:+.2f}%<extra>Portfolio</extra>"
                if mode == "pct"
                else "$%{y:+,.2f}<extra>Portfolio</extra>"
            ),
        ))

        # ── Benchmark overlays — % mode only, not for intraday ──────────
        if mode == "pct" and period != "1d":
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
                    "%{y:+.2f}%<extra>" + tr["buy_date"] + "</extra>"
                    if mode == "pct"
                    else "$%{y:+,.2f}<extra>" + tr["buy_date"] + "</extra>"
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
                fillcolor=hex_to_rgba(theme_tokens.get("INFO", "#378ADD"), 0.1), # ~10% opacity
                line=dict(color=bc, width=2.5),
                hovertemplate=(
                    "%{y:+.2f}%<extra>" + selected + " combined</extra>"
                    if mode == "pct"
                    else "$%{y:+,.2f}<extra>" + selected + " combined</extra>"
                ),
            ))

            if mode == "pct" and period != "1d":
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