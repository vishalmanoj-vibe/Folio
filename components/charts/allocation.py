"""
Portfolio Allocation Chart Component.

Builds a donut chart visualizing the portfolio's market value allocation.
"""

import plotly.graph_objects as go
from config.constants import COLORS

def build_allocation_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly donut chart showing allocation by market value.

    Args:
        holdings: List of enriched holding dictionaries.
        theme_tokens: Dictionary of UI theme colors and base layouts.

    Returns:
        A Plotly go.Figure object.
    """
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
