# components/charts/intel_helpers.py
"""
components/charts/intel_helpers.py
==================================
Shared styles and utilities for Intelligence page charts.
"""
import plotly.graph_objects as go
from components.charts.helpers import create_empty_fig, _LINE_MARGIN, _BAR_MARGIN

_BAR_ROW_PX = 36
_BAR_MIN_H  = 200

def get_bar_height(n_rows: int) -> int:
    return max(_BAR_MIN_H, n_rows * _BAR_ROW_PX + 60)
