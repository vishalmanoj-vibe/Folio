"""
Dividend Income Chart Component.

Builds a bar chart showing the annual dividend income per holding.
"""

import plotly.graph_objects as go
from config.constants import COLORS

def build_dividend_figure(holdings: list[dict], mode: str, theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly bar chart for annual dividend income.

    Args:
        holdings: List of enriched holding dictionaries.
        mode: Display mode, either "dollar" or "pct".
        theme_tokens: Dictionary of UI theme colors and base layouts.

    Returns:
        A Plotly go.Figure object.
    """
    T_SEC       = theme_tokens["T_SEC"]
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
    
    val_key = "div_yield" if mode == "pct" else "annual_div"
    h = [x for x in holdings if x[val_key] > 0]
    if not h:
        fig.add_annotation(text="No dividend data yet — holdings are recent",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
        
    h_s = sorted(h, key=lambda x: x[val_key], reverse=True)
    
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s],
        y=[x[val_key] for x in h_s],
        marker_color=COLORS[1],
        text=[
            f"{x[val_key]:,.2f}%" if mode == "pct" else f"${x[val_key]:,.2f}"
            for x in h_s
        ],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig
