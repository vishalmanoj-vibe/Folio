"""
components/charts/intel_drawdown.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED
from components.charts.intel_helpers import _LINE_BASE

def build_intel_drawdown_chart(dd_dates: list, dd_values: list) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **_LINE_BASE, height=260,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                   zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
        hovermode="x unified",
    )
    if dd_dates and dd_values:
        fig.add_trace(go.Scatter(
            x=dd_dates, y=dd_values,
            mode="lines", name="Drawdown",
            fill="tozeroy", fillcolor="rgba(226,75,74,0.15)",
            line=dict(color=RED, width=1.5),
            hovertemplate="%{y:.2f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
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
