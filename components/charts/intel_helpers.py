"""
components/charts/intel_helpers.py
==================================
Shared styles and utilities for Intelligence page charts.
"""

# Plotly base margins
_LINE_MARGIN = dict(l=16, r=24, t=36, b=16)
_BAR_MARGIN  = dict(l=110, r=60, t=16, b=16)

_BAR_ROW_PX = 36
_BAR_MIN_H  = 200

def get_bar_height(n_rows: int) -> int:
    return max(_BAR_MIN_H, n_rows * _BAR_ROW_PX + 60)

import plotly.graph_objects as go

def create_empty_fig(msg: str = "Waiting for portfolio data…",
                     height: int = 280,
                     bar: bool = False,
                     theme_tokens: dict | None = None) -> go.Figure:
    if theme_tokens:
        base = theme_tokens["PLOTLY_BASE"].copy()
    else:
        from config.constants import PLOTLY_BASE
        base = PLOTLY_BASE.copy()
    
    base["margin"] = _BAR_MARGIN if bar else _LINE_MARGIN
    
    f = go.Figure()
    f.update_layout(
        **base, height=height,
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(color=base["font"]["color"], size=13),
                          opacity=0.6)],
    )
    return f
