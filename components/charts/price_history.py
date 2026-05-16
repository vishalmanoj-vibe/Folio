# components/charts/price_history.py
"""
Price History Chart Component.

Builds a line chart showing historical prices normalized to 100,
starting from each ticker's first purchase date (or a period cutoff).
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import COLORS
from core.engine.utils import get_period_cutoff
from components.charts.helpers import apply_standard_layout

def build_price_chart_figure(
    histories: dict,
    period: str,
    theme_tokens: dict,
    holdings: list | None = None,
) -> go.Figure:
    """
    Build a Plotly line chart of normalized price histories.
    """
    fig = go.Figure()
    
    apply_standard_layout(fig, theme_tokens, height=400, show_legend=True)
    
    # Custom tweaks for price chart
    fig.update_layout(
        margin=dict(t=60, b=30, l=10, r=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1,
            font=dict(size=10, color=theme_tokens["T_SEC"]),
        )
    )
    fig.update_xaxes(tickformat="%b %y", nticks=6)
    fig.update_yaxes(side="right", fixedrange=True)

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

    for i, (t, s) in enumerate(histories.items()):
        if s.empty: continue

        # Determine start date
        if period == "max":
            ticker_cutoff = purchase_map.get(t)
            if ticker_cutoff is not None:
                s = s[s.index >= ticker_cutoff]
        elif calendar_cutoff is not None:
            s = s[s.index >= calendar_cutoff]

        if s.empty or s.iloc[0] == 0:
            continue

        # Normalize to 100
        base = float(s.iloc[0])
        fig.add_trace(go.Scatter(
            x=s.index,
            y=(s / base * 100).round(2),
            name=t, 
            mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=2.0, shape='spline'),
            hovertemplate=f"%{{y:.2f}}<extra>{t}</extra>"
        ))

    if not fig.data:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No price history available", height=400, theme_tokens=theme_tokens)
        
    fig.add_hline(y=100, line_dash="dot", line_color=theme_tokens["BORDER"], line_width=1)
    return fig
