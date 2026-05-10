# components/charts/intel_equity.py
"""
components/charts/intel_equity.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, GREEN, RED
from components.charts.intel_helpers import _LINE_MARGIN

def build_intel_equity_chart(ret_dates: list, ret_values: list, theme_tokens: dict) -> go.Figure:
    fig = go.Figure()
    
    if not ret_dates or not ret_values:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("No performance history available", height=300, theme_tokens=theme_tokens)

    from components.charts.helpers import apply_standard_layout
    apply_standard_layout(fig, theme_tokens, height=300)
    fig.update_yaxes(ticksuffix="%")

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
