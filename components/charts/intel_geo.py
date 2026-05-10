# components/charts/intel_geo.py
"""
components/charts/intel_geo.py
"""
import plotly.graph_objects as go
from config.constants import BORDER, RED, COLORS
from components.charts.intel_helpers import get_bar_height

def build_intel_geo_chart(geo_data: dict, theme_tokens: dict) -> go.Figure:
    geo_s    = sorted(geo_data.items(), key=lambda x: x[1])
    geo_other = next((item for item in geo_s if item[0] == "Other"), None)
    if geo_other:
        geo_s.remove(geo_other)
        geo_s.insert(0, geo_other)
    geo_h    = get_bar_height(len(geo_s))
    
    fig  = go.Figure()
    
    if not geo_s:
        from components.charts.helpers import create_empty_fig
        return create_empty_fig("Geographic exposure data unavailable", height=200, bar=True, theme_tokens=theme_tokens)

    from components.charts.helpers import apply_standard_layout
    apply_standard_layout(fig, theme_tokens, height=geo_h, chart_type="bar")
    fig.update_xaxes(ticksuffix="%", range=[0, 115])

    fig.add_trace(go.Bar(
        x=[v for _, v in geo_s],
        y=[k for k, _ in geo_s],
        orientation="h",
        marker_color=[
            RED if v >= 60 else COLORS[2] if v >= 40 else COLORS[4]
            for _, v in geo_s
        ],
        text=[f"{v:.1f}%" for _, v in geo_s],
        textposition="outside",
        textfont=dict(size=11),
        cliponaxis=False,
    ))
    return fig
