"""
Today's P&L Chart Component.

Builds a bar chart showing the day's absolute P&L per holding.
"""

import plotly.graph_objects as go
from config.constants import GREEN, RED

def build_day_pnl_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly bar chart for today's P&L.

    Args:
        holdings: List of enriched holding dictionaries.
        theme_tokens: Dictionary of UI theme colors and base layouts.

    Returns:
        A Plotly go.Figure object.
    """
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )
    
    h = sorted(holdings, key=lambda x: x["day_pnl"])
    
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
