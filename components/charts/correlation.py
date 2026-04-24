# components/charts/correlation.py
"""
Correlation Heatmap Component.

Builds a heatmap showing the price return correlation between holdings.
"""

import pandas as pd
import plotly.graph_objects as go
from core.engine.utils import get_period_cutoff

def build_corr_figure(histories: dict, period: str, theme_tokens: dict) -> go.Figure:
    """
    Build a Plotly heatmap of daily return correlations.

    Args:
        histories: Dictionary mapping tickers to their historical price DataFrames.
        period: Time period string (e.g., "1mo", "max").
        theme_tokens: Dictionary of UI theme colors and base layouts.

    Returns:
        A Plotly go.Figure object.
    """
    T_SEC       = theme_tokens["T_SEC"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    
    cutoff = get_period_cutoff(period)
    
    if not histories or len(histories) < 2:
        from components.charts.intel_helpers import create_empty_fig
        return create_empty_fig("Need at least 2 holdings with shared history to compute correlation", height=380, theme_tokens=theme_tokens)
        
    dfs = {}
    for t, r in histories.items():
        df = pd.DataFrame(r)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            
        if cutoff is not None:
            df = df[df.index >= cutoff]
            
        s = df["Close"].pct_change().dropna()
        if len(s) >= 10:
            dfs[t] = s
            
    if len(dfs) < 2:
        from components.charts.intel_helpers import create_empty_fig
        return create_empty_fig("Need at least 2 holdings with shared history to compute correlation", height=380, theme_tokens=theme_tokens)
        
    corr  = pd.DataFrame(dfs).corr(min_periods=10).round(2)
    ticks = list(corr.columns)
    
    fig.add_trace(go.Heatmap(
        z=corr.values.tolist(), 
        x=ticks, 
        y=ticks,
        colorscale=[
            [0, theme_tokens["RED"]],    # -1.0
            [0.5, theme_tokens["SURFACE"]], # 0.0
            [1, theme_tokens["GREEN"]]    # +1.0
        ],
        zmin=-1, zmax=1,
        xgap=6, ygap=6, # Creates the "tiled" look
        text=[[f"{v:.2f}" for v in row] for row in corr.values.tolist()],
        texttemplate="%{text}",
        textfont=dict(size=11, color="white", family="Inter, sans-serif"),
        showscale=True,
        colorbar=dict(
            thickness=10,
            len=0.4,
            y=0.5,
            x=1.1,
            tickmode="array",
            tickvals=[-1, 0, 1],
            ticktext=["-1", "0", "+1"],
            tickfont=dict(color=theme_tokens["T_SEC"], size=10),
            outlinecolor="rgba(0,0,0,0)",
        ),
        hoverinfo="none",
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=40, l=40, r=60),
        height=380,
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(size=11, color=theme_tokens["T_SEC"]),
            side="bottom",
            zeroline=False
        ),
        yaxis=dict(
            showgrid=False, 
            tickfont=dict(size=11, color=theme_tokens["T_SEC"]), 
            autorange="reversed",
            zeroline=False
        ),
        uirevision=True,
    )
    return fig
