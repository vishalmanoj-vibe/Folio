"""
Price History Chart Component.

Builds a line chart showing historical prices normalized to 100,
starting from each ticker's first purchase date (or a period cutoff).
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import COLORS
from core.engine.utils import get_period_cutoff


def build_price_chart_figure(
    histories: dict,
    period: str,
    theme_tokens: dict,
    holdings: list | None = None,
) -> go.Figure:
    """
    Build a Plotly line chart of normalized price histories.

    For period="max", each ticker's series is trimmed to start from its
    first purchase date so the chart shows 'since purchase' not full history.
    For all other periods, a calendar cutoff is applied uniformly.

    Args:
        histories: Dictionary mapping tickers to their historical price DataFrames.
        period: Time period string (e.g., "1mo", "max").
        theme_tokens: Dictionary of UI theme colors and base layouts.
        holdings: List of holding dicts (used to find first_purchase per ticker).

    Returns:
        A Plotly go.Figure object.
    """
    T_SEC = theme_tokens["T_SEC"]
    T_PRI = theme_tokens["T_PRI"]
    
    layout = theme_tokens["PLOTLY_BASE"].copy()
    layout.update(dict(
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(size=11, color=T_SEC),
            zeroline=False,
            tickformat="%b %y",
            nticks=6,
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)", 
            tickfont=dict(size=11, color=T_SEC),
            zeroline=False,
            side="right", # Values on right as in mockup
            fixedrange=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="right",
            x=1,
            font=dict(size=10, color=T_SEC),
        ),
        hovermode="x unified",
        margin=dict(t=60, b=30, l=10, r=40), # Space for legend and right-axis
        height=400,
    ))
    
    fig = go.Figure()
    fig.update_layout(layout)

    # Build a lookup of ticker → first_purchase date for "max" (since purchase) mode
    purchase_map: dict[str, pd.Timestamp] = {}
    if holdings and period == "max":
        for h in holdings:
            ticker = h.get("ticker", "")
            fp = h.get("first_purchase")
            if ticker and fp:
                purchase_map[ticker] = pd.to_datetime(fp)

    # For non-max periods, use a single calendar cutoff for all tickers
    calendar_cutoff = get_period_cutoff(period)

    for i, (t, recs) in enumerate(histories.items()):
        df = pd.DataFrame(recs)
        if df.empty: continue

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        # Determine start date
        if period == "max":
            ticker_cutoff = purchase_map.get(t)
            if ticker_cutoff is not None:
                df = df[df.index >= ticker_cutoff]
        elif calendar_cutoff is not None:
            df = df[df.index >= calendar_cutoff]

        if df.empty or df["Close"].iloc[0] == 0:
            continue

        # Normalize to 100
        base = df["Close"].iloc[0]
        fig.add_trace(go.Scatter(
            x=df.index,
            y=(df["Close"] / base * 100).round(2),
            name=t, 
            mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=2.0, shape='spline'), # Spline for smoother look
            hovertemplate=f"{t}: %{{y:.2f}}<extra></extra>"
        ))

    fig.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.2)", line_width=1)
    return fig
