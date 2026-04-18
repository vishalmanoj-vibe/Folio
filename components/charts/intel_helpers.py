"""
components/charts/intel_helpers.py
==================================
Shared styles and utilities for Intelligence page charts.
"""

from config.constants import BG, SURFACE, T_PRI, T_SEC

# Plotly base for line / area charts (tight margins, labels fit inside)
_LINE_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=24, t=36, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,  # Preserve zoom/pan state across auto-refreshes
)

# Plotly base for horizontal bar charts — wide left margin for y-axis labels
_BAR_BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=12),
    margin=dict(l=110, r=60, t=16, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    showlegend=False,
    uirevision=True,  # Preserve state across auto-refreshes
)

_BAR_ROW_PX = 36
_BAR_MIN_H  = 200

def get_bar_height(n_rows: int) -> int:
    return max(_BAR_MIN_H, n_rows * _BAR_ROW_PX + 60)

import plotly.graph_objects as go

def create_empty_fig(msg: str = "Waiting for portfolio data…",
                     height: int = 280,
                     bar: bool = False) -> go.Figure:
    base = _BAR_BASE if bar else _LINE_BASE
    f = go.Figure()
    f.update_layout(
        **base, height=height,
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(color=T_SEC, size=13))],
    )
    return f
