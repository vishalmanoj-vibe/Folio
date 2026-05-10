# components/charts/performance_bars.py
"""
components/charts/performance_bars.py
=====================================
High-density horizontal lollipop chart for performance metrics.
"""

import plotly.graph_objects as go

def build_performance_lollipops(
    data: list[dict], 
    theme_tokens: dict,
    mode: str = "pct"
) -> go.Figure:
    """
    Build a horizontal lollipop chart for portfolio performance.
    """
    fig = go.Figure()
    
    # Base Layout (Standard for both empty and populated states)
    base_layout = dict(
        paper_bgcolor=theme_tokens["BG"],
        plot_bgcolor=theme_tokens["BG"],
        font=dict(color=theme_tokens["T_PRI"], family="Inter, sans-serif"),
        margin=dict(t=10, b=10, l=40, r=20),
        uirevision=True,
    )
    
    if not data:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No performance data available", height=300, theme_tokens=theme_tokens)

    # Sort by value (Best performers at top)
    data = sorted(data, key=lambda x: x["value"], reverse=True)
    
    tickers = [d["ticker"] for d in data]
    values = [d["value"] for d in data]
    colors = [theme_tokens["GREEN"] if v >= 0 else theme_tokens["RED"] for v in values]

    # 1. Stems (Line from 0 to value)
    for i, d in enumerate(data):
        fig.add_trace(go.Scatter(
            x=[0, d["value"]],
            y=[i, i],
            mode="lines",
            line=dict(color=theme_tokens["BORDER"], width=2),
            hoverinfo="skip"
        ))

    # 2. Lollipops (Dots)
    fig.add_trace(go.Scatter(
        x=values,
        y=list(range(len(data))),
        mode="markers",
        marker=dict(
            color=colors,
            size=10,
            line=dict(color=theme_tokens["BG"], width=1.5)
        ),
        text=tickers,
        customdata=values,
        hovertemplate="<b>%{text}</b><br>Amount: $%{customdata:,.2f}<extra></extra>"
    ))

    # Layout configuration
    fig.update_layout(
        **base_layout,
        showlegend=False,
        xaxis=dict(
            title=dict(text="Amount ($)", font=dict(size=10, color="#8a8880")),
            tickfont=dict(color=theme_tokens["T_SEC"], size=10),
            gridcolor=theme_tokens["BORDER"],
            zerolinecolor=theme_tokens["BORDER"],
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(data))),
            ticktext=tickers,
            tickfont=dict(color=theme_tokens["T_PRI"], size=11, weight=600),
            autorange="reversed",
            showgrid=False,
            zeroline=False
        ),
        height=max(400, len(data) * 35)
    )

    return fig
