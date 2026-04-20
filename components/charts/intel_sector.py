"""
components/charts/intel_sector.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED, COLORS
from components.charts.intel_helpers import _BAR_MARGIN, get_bar_height

def build_intel_sector_chart(sec_exp: dict, theme_tokens: dict) -> go.Figure:
    sec_s   = sorted(sec_exp.items(), key=lambda x: x[1])
    sec_other = next((item for item in sec_s if item[0] == "Other"), None)
    if sec_other:
        sec_s.remove(sec_other)
        sec_s.insert(0, sec_other)
    sec_h   = get_bar_height(len(sec_s))
    fig = go.Figure()
    
    base = theme_tokens["PLOTLY_BASE"].copy()
    base["margin"] = _BAR_MARGIN
    base["showlegend"] = False

    layout = base.copy()
    layout.update(dict(
        height=sec_h,
        xaxis=dict(gridcolor=theme_tokens["BORDER"], ticksuffix="%", range=[0, 115]),
        yaxis=dict(showgrid=False),
    ))
    fig.update_layout(layout)
    if sec_s:
        fig.add_trace(go.Bar(
            x=[v for _, v in sec_s],
            y=[k for k, _ in sec_s],
            orientation="h",
            marker_color=[
                RED if v >= 40 else COLORS[2] if v >= 25 else COLORS[0]
                for _, v in sec_s
            ],
            text=[f"{v:.1f}%" for _, v in sec_s],
            textposition="outside",
            textfont=dict(size=11),
            cliponaxis=False,
        ))
    return fig
