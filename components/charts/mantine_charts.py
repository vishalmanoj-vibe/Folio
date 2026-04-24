# components/charts/mantine_charts.py
"""
components/charts/mantine_charts.py
===================================
Premium SaaS-style charts using Dash Mantine Components.
"""

import dash_mantine_components as dmc
from config.constants import COLORS, GREEN, RED

def create_pnl_bar_dmc(holdings: list[dict], mode: str = "dollar") -> dmc.BarChart:
    """
    Create a Mantine BarChart for Unrealised P&L.
    """
    data = []
    for h in holdings:
        val = h.get("pnl", 0) if mode == "dollar" else h.get("pnl_pct", 0)
        data.append({
            "ticker": h["ticker"],
            "value": round(val, 2),
            "color": GREEN if val >= 0 else RED
        })
    
    # Sort by value descending
    data = sorted(data, key=lambda x: x["value"], reverse=True)

    return dmc.BarChart(
        h=300,
        data=data,
        dataKey="ticker",
        series=[{"name": "value", "label": "P&L"}],
        xAxisLabel="Ticker",
        yAxisLabel="$" if mode == "dollar" else "%",
        withTooltip=True,
        gridAxis="xy",
        strokeDasharray="0",
        tickLine="xy",
    )

def create_day_pnl_dmc(holdings: list[dict], mode: str = "dollar") -> dmc.BarChart:
    """
    Create a Mantine BarChart for Today's P&L.
    """
    data = []
    for h in holdings:
        val = h.get("day_pnl", 0) if mode == "dollar" else h.get("day_chg_pct", 0)
        data.append({
            "ticker": h["ticker"],
            "value": round(val, 2),
            "color": GREEN if val >= 0 else RED
        })
    
    return dmc.BarChart(
        h=300,
        data=data,
        dataKey="ticker",
        series=[{"name": "value", "label": "Day P&L"}],
        xAxisLabel="Ticker",
        yAxisLabel="$" if mode == "dollar" else "%",
        withTooltip=True,
        gridAxis="xy",
        strokeDasharray="0",
        tickLine="xy",
    )

def create_allocation_dmc(holdings: list[dict]) -> dmc.DonutChart:
    """
    Create a Mantine DonutChart for Portfolio Allocation.
    """
    total_val = sum(h.get("mkt_value", 0) for h in holdings)
    data = []
    for i, h in enumerate(holdings):
        val = h.get("mkt_value", 0)
        weight = (val / total_val * 100) if total_val else 0
        data.append({
            "name": h["ticker"],
            "value": round(weight, 1),
            "color": COLORS[i % len(COLORS)]
        })
    
    return dmc.DonutChart(
        data=data,
        withLabels=True,
        withTooltip=True,
        size=220,
        thickness=25,
        paddingAngle=5,
        tooltipDataSource="segment",
        chartLabel="Allocation",
    )

def create_exposure_donut_dmc(exposure_data: list[dict], title: str = "") -> dmc.DonutChart:
    """
    Create a Mantine DonutChart for Sector/Geographic exposure.
    Expects data as list of {"name": str, "value": float, "color": str}
    """
    return dmc.DonutChart(
        data=exposure_data,
        withLabels=True,
        withTooltip=True,
        size=200,
        thickness=20,
        paddingAngle=10,
        tooltipDataSource="segment",
    )

def create_dividend_dmc(holdings: list[dict]) -> dmc.BarChart:
    """
    Create a Mantine BarChart for Dividend Income.
    """
    data = []
    for h in holdings:
        div = h.get("annual_div", 0)
        if div > 0:
            data.append({
                "ticker": h["ticker"],
                "Income": round(div, 2)
            })
    
    # Sort by income descending
    data = sorted(data, key=lambda x: x["Income"], reverse=True)

    return dmc.BarChart(
        h=300,
        data=data,
        dataKey="ticker",
        series=[{"name": "Income", "color": "indigo.6"}],
        withTooltip=True,
        gridAxis="xy",
        strokeDasharray="0",
        tickLine="xy",
    )
