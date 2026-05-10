# components/charts/intel_drawdown.py
"""
components/charts/intel_drawdown.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED
from components.charts.intel_helpers import _LINE_MARGIN

def build_intel_drawdown_chart(dd_dates: list, dd_values: list, theme_tokens: dict) -> go.Figure:
    fig = go.Figure()
    base = theme_tokens["PLOTLY_BASE"].copy()
    base["margin"] = _LINE_MARGIN

    layout = base.copy()
    layout.update(dict(
        height=300,
        showlegend=False,
        margin=dict(l=16, r=16, t=36, b=16),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=theme_tokens["BORDER"], ticksuffix="%",
                   zeroline=True, zerolinecolor=theme_tokens["BORDER"], zerolinewidth=1),
        hovermode="x unified",
        uirevision=True,
    ))
    if not dd_dates or not dd_values:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No drawdown history available", height=300, theme_tokens=theme_tokens)

    fig.update_layout(layout)
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
