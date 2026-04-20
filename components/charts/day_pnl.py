"""
Today's P&L Chart Component.

Builds a bar chart showing the day's absolute P&L per holding.
"""

import plotly.graph_objects as go
from config.constants import GREEN, RED

def build_day_pnl_figure(holdings: list[dict], mode: str, theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly bar chart for today's P&L.

    Args:
        holdings: List of enriched holding dictionaries.
        mode: Display mode, either "dollar" or "pct".
        theme_tokens: Dictionary of UI theme colors and base layouts.

    Returns:
        A Plotly go.Figure object.
    """
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, 
                   ticksuffix="%" if mode == "pct" else "",
                   tickprefix="" if mode == "pct" else "$"),
        **PLOTLY_BASE,
    )
    
    val_key = "day_chg_pct" if mode == "pct" else "day_pnl"
    h = sorted(holdings, key=lambda x: x[val_key])
    
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x[val_key] for x in h],
        marker_color=[GREEN if x[val_key] >= 0 else RED for x in h],
        text=[
            f"{'+' if x[val_key]>=0 else ''}{x[val_key]:,.2f}{'%' if mode=='pct' else ''}"
            if mode == "pct" else
            f"{'+' if x[val_key]>=0 else ''}${abs(x[val_key]):,.2f}"
            for x in h
        ],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig
