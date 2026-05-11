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
from components.charts.helpers import build_benchmark_traces, hex_to_rgba, apply_standard_layout

import logging
logger = logging.getLogger(__name__)

def _build_intraday_figure(
    fig: "go.Figure",
    holdings: list[dict],
    mode: str,
    theme_tokens: dict,
    selected: str = "Portfolio",
) -> "go.Figure":
    """
    Build the 'Today' intraday P&L chart.
    """
    import json as _json, os as _os
    from datetime import datetime as _dt
    from services.market.market_status import get_previous_trading_session_start

    GREEN_C = theme_tokens.get("GREEN", "#1D9E75")
    RED_C   = theme_tokens.get("RED",   "#E24B4A")

    now_syd      = pd.Timestamp.now(tz="Australia/Sydney")
    today_str    = now_syd.strftime("%Y-%m-%d")
    chart_start  = get_previous_trading_session_start()
    market_close = pd.Timestamp(f"{today_str} 16:15:00", tz="Australia/Sydney")

    cache_path = _os.path.join("data", "cache", f"intraday_{today_str}.json")
    session_data: dict = {}
    try:
        if _os.path.exists(cache_path):
            with open(cache_path) as _f:
                session_data = _json.load(_f)
    except Exception:
        pass

    if not session_data:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("Waiting for market session data (ASX opens 10:00 Sydney Time) …", height=380, theme_tokens=theme_tokens)

    # Filter tickers if a specific one is selected
    target_tickers = [selected] if selected != "Portfolio" else [h["ticker"] for h in holdings]
    
    prev_close_map  = {h["ticker"]: h.get("prev_close", 0.0) for h in holdings}
    total_shares_map = {h["ticker"]: h.get("total_shares", 0.0) for h in holdings}

    all_series: list[pd.Series] = []

    for ticker in target_tickers:
        points = session_data.get(ticker)
        if not points: continue
        
        prev_close   = prev_close_map.get(ticker, 0.0)
        total_shares = total_shares_map.get(ticker, 0.0)
        if prev_close <= 0 or (selected == "Portfolio" and total_shares <= 0):
            continue

        df = pd.DataFrame(points)
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize("Australia/Sydney")
        df = df.sort_values("Date").drop_duplicates("Date")
        df = df[(df["Date"] >= chart_start) & (df["Date"] <= market_close)]

        if df.empty:
            continue

        price_s = df.set_index("Date")["Close"]
        price_s = price_s[price_s > 0]
        if not price_s.empty:
            price_s = price_s.resample('5min').last().ffill()

        if price_s.empty:
            continue

        if mode == "pct":
            day_s = ((price_s - prev_close) / prev_close * 100).round(4)
        else:
            day_s = ((price_s - prev_close) * (total_shares if selected == "Portfolio" else 1)).round(2)

        day_s.name = ticker
        all_series.append(day_s)

    if not all_series:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig(f"Intraday data unavailable for {selected}", height=380, theme_tokens=theme_tokens)

    combined = pd.concat(all_series, axis=1, sort=True).sort_index().ffill().fillna(0)

    if selected == "Portfolio":
        if mode == "pct":
            weights = []
            for ticker in combined.columns:
                h = next((x for x in holdings if x["ticker"] == ticker), {})
                weights.append(h.get("total_cost", h.get("prev_close", 1) * h.get("total_shares", 1)))
            
            if weights and len(weights) == combined.shape[1]:
                total_w    = sum(weights)
                weight_arr = [w / total_w for w in weights]
                portfolio_s = (combined * weight_arr).sum(axis=1).round(4)
            else:
                portfolio_s = combined.mean(axis=1).round(4)
        else:
            portfolio_s = combined.sum(axis=1).round(2)
    else:
        # Single ticker
        portfolio_s = combined.iloc[:, 0]

    # Split into Previous Session and Today for independent coloring
    today_start = pd.Timestamp.now(tz="Australia/Sydney").normalize()
    segments = [
        ("Previous", portfolio_s[portfolio_s.index < today_start]),
        ("Today",    portfolio_s[portfolio_s.index >= today_start])
    ]

    for name, s in segments:
        if s.empty: continue
        
        lv = float(s.iloc[-1])
        line_color = GREEN_C if lv >= 0 else RED_C
        fill_color = hex_to_rgba(line_color, 0.12)

        fig.add_trace(go.Scatter(
            x=s.index,
            y=s.values,
            name=f"{selected} {name}",
            mode="lines",
            fill="tozeroy",
            fillcolor=fill_color,
            line=dict(color=line_color, width=2.5),
            hovertemplate=(
                "<b>%{x|%a %d %b, %H:%M}</b><br>"
                + ("%{y:+.2f}%<extra>Day change</extra>" if mode == "pct"
                   else "$%{y:+,.2f}<extra>Day P&L</extra>")
            ),
        ))

    # For the summary annotation, use the overall last value (Today's status)
    overall_last = float(portfolio_s.iloc[-1]) if len(portfolio_s) else 0.0
    anno_color = GREEN_C if overall_last >= 0 else RED_C

    sign  = "+" if overall_last >= 0 else ""
    label = f"{sign}{overall_last:.2f}%" if mode == "pct" else f"{sign}${overall_last:,.2f}"
    fig.add_annotation(
        text=f"<b>{label}</b>",
        xref="paper", yref="paper",
        x=0.01, y=0.97,
        xanchor="left", yanchor="top",
        showarrow=False,
        font=dict(size=14, color=anno_color),
        bgcolor=theme_tokens.get("BG", "#1A1A2E"),
        borderpad=4,
    )

    if not fig.data:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No intraday data found for this selection", height=380, theme_tokens=theme_tokens)
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
    """
    fig = go.Figure()
    apply_standard_layout(fig, theme_tokens, height=380)

    # Custom P&L overrides
    fig.update_layout(
        margin=dict(t=30, b=30, l=60, r=20),
        xaxis=dict(type="date", showspikes=True, spikecolor=theme_tokens["T_SEC"], spikethickness=1, spikedash="dash"),
        yaxis=dict(
            ticksuffix="%" if mode == "pct" else "",
            tickprefix="" if mode == "pct" else "$",
        )
    )
    
    if period == "1d":
        fig.update_layout(xaxis=dict(
            tickformat="%H:%M",
            dtick=30 * 60 * 1000,
            tickangle=0,
        ))
        from services.market.market_status import get_previous_trading_session_start
        chart_start = get_previous_trading_session_start()
        range_start = chart_start.isoformat()
        range_end   = pd.Timestamp.now(tz="Australia/Sydney").replace(hour=16, minute=15, second=0).isoformat()
        
        fig.update_xaxes(
            range=[range_start, range_end],
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[16.25, 10], pattern="hour"),
            ],
            dtick=None,
            nticks=10,
        )
    else:
        fig.update_xaxes(tickformat=None)

    if period == "1d":
        return _build_intraday_figure(fig, holdings, mode, theme_tokens, selected=selected)

    cutoff = get_period_cutoff(period)

    def build_series(tr):
        idx        = pd.to_datetime(tr["dates"])
        pnl_series = pd.Series(tr["pnl"], index=idx)
        buy_dt     = pd.to_datetime(tr["buy_date"])
        if period != "1d" and buy_dt not in pnl_series.index:
            pnl_series.loc[buy_dt] = 0.0
        pnl_series = pnl_series.sort_index()
        cost_series = pd.Series(tr["shares"] * tr["buy_price"], index=pnl_series.index)
        if cutoff is not None:
            effective   = max(cutoff, buy_dt) if period != "1d" else cutoff
            pnl_series  = pnl_series[pnl_series.index   >= effective]
            cost_series = cost_series[cost_series.index >= effective]
        return pnl_series, cost_series, buy_dt

    color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}

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
            from components.charts.helpers import create_empty_fig
            return create_empty_fig("No history data found for this selection", height=380, theme_tokens=theme_tokens)

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
        lv = float(y.iloc[-1]) if len(y) else 0

        fig.add_trace(go.Scatter(
            x=cpnl.index, y=y,
            name="Portfolio",
            mode="lines",
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.12) if lv >= 0 else hex_to_rgba(RED, 0.10),
            line=dict(color=GREEN if lv >= 0 else RED, width=2.5),
            hovertemplate=(
                "%{y:+.2f}%<extra>Portfolio</extra>"
                if mode == "pct"
                else "$%{y:+,.2f}<extra>Portfolio</extra>"
            ),
        ))

        if mode == "pct" and period != "1d":
            for trace in build_benchmark_traces(period, theme_tokens=theme_tokens, portfolio_start=cpnl.index.min()):
                fig.add_trace(trace)
            fig.add_annotation(
                text="Benchmarks normalised to period start",
                xref="paper", yref="paper",
                x=1.0, y=1.02, xanchor="right", yanchor="bottom",
                showarrow=False,
                font=dict(size=10, color=theme_tokens["T_SEC"]),
            )

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
    else:
        hm = next((h for h in holdings if h["ticker"] == selected), None)
        if not hm:
            from components.charts.helpers import create_empty_fig
            return create_empty_fig(f"Ticker {selected} not found in holdings", height=380, theme_tokens=theme_tokens)

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
            lv = float(y.iloc[-1]) if len(y) else 0

            fig.add_trace(go.Scatter(
                x=cpnl.index, y=y,
                name=f"{selected} (combined)",
                mode="lines",
                fill="tozeroy",
                fillcolor=hex_to_rgba(GREEN, 0.12) if lv >= 0 else hex_to_rgba(RED, 0.10),
                line=dict(color=GREEN if lv >= 0 else RED, width=2.5),
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
                    x=1.0, y=1.02, xanchor="right", yanchor="bottom",
                    showarrow=False,
                    font=dict(size=10, color=theme_tokens["T_SEC"]),
                )

    fig.add_hline(y=0, line_color=theme_tokens["BORDER"], line_width=0.8)
    return fig