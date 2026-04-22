"""
components/charts/intel_volatility.py
"""
import math
import plotly.graph_objects as go
from config.constants import BORDER, GREEN, RED, COLORS
from components.charts.intel_helpers import _BAR_MARGIN, get_bar_height

def build_intel_volatility_chart(ticker_vols: dict, theme_tokens: dict) -> go.Figure:
    tv = sorted(
        [(t, v) for t, v in ticker_vols.items()
         if v is not None and not math.isnan(v)],
        key=lambda x: x[1],
    )
    
    T_PRI = theme_tokens["T_PRI"]
    T_SEC = theme_tokens["T_SEC"]
    GREEN = "#1D9E75"
    RED   = "#E24B4A"
    AMBER = "#EF9F27"
    
    if not tv:
        from components.charts.intel_helpers import create_empty_fig
        return create_empty_fig("Insufficient data for this period", height=120, bar=True, theme_tokens=theme_tokens)

    labels, values = zip(*tv)
    # Colors: Green < 12%, Amber 12-20%, Red > 20%
    colors = [RED if v > 20 else AMBER if v > 12 else GREEN for v in values]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
        ),
        text=[f"{v:.2f}%" for v in values],
        textposition="outside",
        textfont=dict(size=12, color=colors),
        cliponaxis=False,
        width=0.3, # Progress bar look
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=T_PRI, size=12),
        margin=dict(l=0, r=60, t=0, b=0),
        xaxis=dict(visible=False, range=[0, max(values)*1.3]),
        yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=12, color=T_SEC)),
        height=max(len(tv)*38, 120),
        showlegend=False,
        hovermode=False,
        uirevision=True,
    )
    return fig
