"""
Price History Chart Component.

Builds a line chart showing historical prices normalized to 100,
starting from each ticker's first purchase date (or a period cutoff).
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import COLORS
from components.charts.helpers import _period_cutoff


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
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]

    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER),
        **PLOTLY_BASE
    )

    # Build a lookup of ticker → first_purchase date for "max" (since purchase) mode
    purchase_map: dict[str, pd.Timestamp] = {}
    if holdings and period == "max":
        for h in holdings:
            ticker = h.get("ticker", "")
            fp = h.get("first_purchase")
            if ticker and fp:
                purchase_map[ticker] = pd.to_datetime(fp)

    # For non-max periods, use a single calendar cutoff for all tickers
    calendar_cutoff = _period_cutoff(period)  # None when period == "max"

    for i, (t, recs) in enumerate(histories.items()):
        df = pd.DataFrame(recs)
        if df.empty:
            continue

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        # Determine the effective start date for this ticker
        if period == "max":
            # Trim to first purchase date so we only show "since you bought it"
            ticker_cutoff = purchase_map.get(t)
            if ticker_cutoff is not None:
                df = df[df.index >= ticker_cutoff]
        elif calendar_cutoff is not None:
            df = df[df.index >= calendar_cutoff]

        if df.empty or df["Close"].iloc[0] == 0:
            continue

        # Normalize to 100 at the start of the (trimmed) window
        base = df["Close"].iloc[0]
        fig.add_trace(go.Scatter(
            x=df.index.strftime("%Y-%m-%d").tolist(),
            y=(df["Close"] / base * 100).round(2),
            name=t, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=1.8),
        ))

    fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
    return fig
