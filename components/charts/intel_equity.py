# components/charts/intel_equity.py
"""
components/charts/intel_equity.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, GREEN, RED
from components.charts.intel_helpers import _LINE_MARGIN

def build_intel_equity_chart(ret_dates: list, ret_values: list, theme_tokens: dict) -> go.Figure:
    fig = go.Figure()
    
    base = theme_tokens["PLOTLY_BASE"].copy()
    base["margin"] = _LINE_MARGIN
    
    layout = base.copy()
    layout.update(dict(
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=theme_tokens["BORDER"], ticksuffix="%",
                   zeroline=True, zerolinecolor=theme_tokens["BORDER"], zerolinewidth=1),
        hovermode="x unified",
    ))
    if not ret_dates or not ret_values:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No performance history available", height=300, theme_tokens=theme_tokens)

    fig.update_layout(layout)
    lv = ret_values[-1]
    fig.add_trace(go.Scatter(
        x=ret_dates, y=ret_values,
        mode="lines", name="Portfolio",
        fill="tozeroy",
        fillcolor="rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)",
        line=dict(color=GREEN if lv >= 0 else RED, width=2),
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=theme_tokens["BORDER"], line_width=0.8)
    return fig
