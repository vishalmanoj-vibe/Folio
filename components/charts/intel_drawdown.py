# components/charts/intel_drawdown.py
"""
components/charts/intel_drawdown.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED

def build_intel_drawdown_chart(dd_dates: list, dd_values: list, theme_tokens: dict) -> go.Figure:
    fig = go.Figure()

    if not dd_dates or not dd_values:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No drawdown history available", height=300, theme_tokens=theme_tokens)

    from components.charts.helpers import apply_standard_layout
    apply_standard_layout(fig, theme_tokens, height=300)
    fig.update_yaxes(ticksuffix="%")

    fig.add_trace(go.Scatter(
        x=dd_dates, y=dd_values,
        mode="lines", name="Drawdown",
        fill="tozeroy", fillcolor="rgba(226,75,74,0.15)",
        line=dict(color=RED, width=1.5),
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=theme_tokens["BORDER"], line_width=0.8)
    
    # Annotate max drawdown point
    min_v   = min(dd_values)
    min_idx = dd_values.index(min_v)
    fig.add_trace(go.Scatter(
        x=[dd_dates[min_idx]], y=[min_v],
        mode="markers+text",
        marker=dict(color=RED, size=8),
        text=[f"Max {min_v:.1f}%"],
        textposition="top right",
        textfont=dict(size=10, color=RED),
        showlegend=False, hoverinfo="skip",
    ))
    return fig
