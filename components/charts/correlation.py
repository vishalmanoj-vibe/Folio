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
        from components.charts.helpers import create_empty_fig
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
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("Need at least 2 holdings with shared history to compute correlation", height=380, theme_tokens=theme_tokens)
        
    corr  = pd.DataFrame(dfs).corr(min_periods=10).round(2)
    ticks = list(corr.columns)
    
    # Filter for lower triangle (j < i)
    x_data = []
    y_data = []
    size_data = []
    color_data = []
    text_data = []
    
    for i in range(len(ticks)):
        for j in range(i):
            val = corr.iloc[i, j]
            if pd.isna(val):
                continue
            x_data.append(ticks[j])
            y_data.append(ticks[i])
            size_data.append(abs(val) * 40)
            color_data.append(val)
            text_data.append(f"{val:.2f}")

    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode="markers+text",
        text=text_data,
        textfont=dict(size=10, color="white", family="Inter, sans-serif"),
        marker=dict(
            size=size_data,
            color=color_data,
            colorscale=[
                [0.0, theme_tokens["GREEN"]],
                [0.5, theme_tokens["WARNING"]], 
                [1.0, theme_tokens["RED"]]
            ],
            cmin=-1,
            cmax=1,
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
            line=dict(width=0.5, color="rgba(255,255,255,0.1)")
        ),
        hoverinfo="none",
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=60, l=80, r=80),
        height=420,
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(size=11, color=theme_tokens["T_SEC"]),
            side="bottom",
            zeroline=False,
            categoryorder="array",
            categoryarray=ticks[:-1]
        ),
        yaxis=dict(
            showgrid=False, 
            tickfont=dict(size=11, color=theme_tokens["T_SEC"]), 
            zeroline=False,
            categoryorder="array",
            categoryarray=ticks[::-1]
        ),
        uirevision=True,
    )
    return fig
