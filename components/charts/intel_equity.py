"""
components/charts/intel_equity.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, GREEN, RED
from components.charts.intel_helpers import _LINE_BASE

def build_intel_equity_chart(ret_dates: list, ret_values: list) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **_LINE_BASE, height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, ticksuffix="%",
                   zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
        hovermode="x unified",
    )
    if ret_dates and ret_values:
        lv = ret_values[-1]
        fig.add_trace(go.Scatter(
            x=ret_dates, y=ret_values,
            mode="lines", name="Portfolio",
            fill="tozeroy",
            fillcolor="rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)",
            line=dict(color=GREEN if lv >= 0 else RED, width=2),
            hovertemplate="%{y:.2f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
    return fig
