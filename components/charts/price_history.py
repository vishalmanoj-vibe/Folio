"""
Price History Chart Component.

Builds a line chart showing historical prices normalized to 100.
"""

import pandas as pd
import plotly.graph_objects as go
from config.constants import COLORS

def build_price_chart_figure(histories: dict, theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly line chart of normalized price histories.

    Args:
        histories: Dictionary mapping tickers to their historical price DataFrames.
        theme_tokens: Dictionary of UI theme colors and base layouts.

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
