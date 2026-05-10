# components/charts/intel_sector.py
"""
components/charts/intel_sector.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED, COLORS
from components.charts.intel_helpers import get_bar_height

def build_intel_sector_chart(sec_exp: dict, theme_tokens: dict) -> go.Figure:
    sec_s   = sorted(sec_exp.items(), key=lambda x: x[1])
    sec_other = next((item for item in sec_s if item[0] == "Other"), None)
    if sec_other:
        sec_s.remove(sec_other)
        sec_s.insert(0, sec_other)
    sec_h   = get_bar_height(len(sec_s))
    
    fig = go.Figure()
    
    if not sec_s:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("Sector exposure data unavailable", height=200, bar=True, theme_tokens=theme_tokens)

    from components.charts.helpers import apply_standard_layout
    apply_standard_layout(fig, theme_tokens, height=sec_h, chart_type="bar")
    fig.update_xaxes(ticksuffix="%", range=[0, 115])

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
