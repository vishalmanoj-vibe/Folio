"""
components/charts/intel_volatility.py
"""
import math
import plotly.graph_objects as go
from config.constants import BORDER, GREEN, RED, COLORS
from components.charts.intel_helpers import _BAR_BASE, get_bar_height

def build_intel_volatility_chart(ticker_vols: dict) -> go.Figure:
    tv = sorted(
        [(t, v) for t, v in ticker_vols.items()
         if v is not None and not math.isnan(v)],
        key=lambda x: x[1],
    )
    vol_h = get_bar_height(len(tv))
    fig = go.Figure()
    fig.update_layout(**_BAR_BASE, height=vol_h,
                      xaxis=dict(gridcolor=BORDER, ticksuffix="%"),
                      yaxis=dict(showgrid=False))
    if tv:
        fig.add_trace(go.Bar(
            x=[v for _, v in tv],
            y=[t for t, _ in tv],
            orientation="h",
            marker_color=[
                RED if v > 20 else COLORS[2] if v > 12 else GREEN
                for _, v in tv
            ],
            text=[f"{v:.1f}%" for _, v in tv],
            textposition="outside",
            textfont=dict(size=11),
            cliponaxis=False,
        ))
    return fig
