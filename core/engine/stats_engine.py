"""
core/engine/stats_engine.py
============================
Portfolio statistics and formatting logic.

Extracted from callbacks/core_callbacks.py so callbacks contain
zero business logic.

Exported functions
------------------
compute_portfolio_stats(holdings)
    Aggregate totals used by the stat cards row.

build_live_table_rows(holdings)
    Pre-formatted row dicts for the live positions table.
    Callbacks convert these to html.Tr — no math there.
"""

from __future__ import annotations

from config.constants import GREEN, RED


def compute_portfolio_stats(holdings: list[dict]) -> dict:
    """
    Aggregate portfolio-level totals from enriched holdings.

    Parameters
    ----------
    holdings : list of enriched holding dicts from fetch_live()

    Returns
    -------
    dict with keys:
        total_val, total_cost, total_pnl, pnl_pct,
        total_day, annual_div, port_yield
    """
    total_val  = sum(x["mkt_value"]  for x in holdings)
    total_cost = sum(x["total_cost"] for x in holdings)
    total_pnl  = total_val - total_cost
    pnl_pct    = (total_pnl / total_cost * 100) if total_cost else 0.0
    total_day  = sum(x["day_pnl"]    for x in holdings)
    annual_div = sum(x["annual_div"] for x in holdings)
    port_yield = (annual_div / total_val * 100) if total_val else 0.0

    return {
        "total_val":  round(total_val,  2),
        "total_cost": round(total_cost, 2),
        "total_pnl":  round(total_pnl,  2),
        "pnl_pct":    round(pnl_pct,    2),
        "total_day":  round(total_day,  2),
        "annual_div": round(annual_div, 2),
        "port_yield": round(port_yield, 2),
    }


def build_live_table_rows(holdings: list[dict]) -> list[dict]:
    """
    Sort holdings by market value and attach pre-computed display fields
    (sign strings, colours) so the callback renders rows with no math.

    Parameters
    ----------
    holdings : list of enriched holding dicts

    Returns
    -------
    list of row dicts, each containing every field the table cell needs:
        ticker, name, total_shares, avg_cost, last_price,
        day_chg, day_chg_pct, day_chg_color, day_chg_sign,
        day_high, day_low, mkt_value, total_cost,
        pnl, pnl_pct, pnl_color, pnl_sign,
        day_pnl, day_pnl_color, day_pnl_sign,
        div_yield
    """
    rows = []
    for x in sorted(holdings, key=lambda v: v["mkt_value"], reverse=True):
        day_pos = x["day_chg"] >= 0
        pnl_pos = x["pnl"] >= 0
        dpnl_pos = x["day_pnl"] >= 0
        rows.append({
            "ticker":        x["ticker"],
            "name":          x.get("name", ""),
            "total_shares":  x["total_shares"],
            "avg_cost":      x["avg_cost"],
            "last_price":    x["last_price"],
            "day_chg":       x["day_chg"],
            "day_chg_pct":   x["day_chg_pct"],
            "day_chg_color": GREEN if day_pos else RED,
            "day_chg_sign":  "+" if day_pos else "",
            "day_high":      x["day_high"],
            "day_low":       x["day_low"],
            "mkt_value":     x["mkt_value"],
            "total_cost":    x["total_cost"],
            "pnl":           x["pnl"],
            "pnl_pct":       x["pnl_pct"],
            "pnl_color":     GREEN if pnl_pos else RED,
            "pnl_sign":      "+" if pnl_pos else "",
            "day_pnl":       x["day_pnl"],
            "day_pnl_color": GREEN if dpnl_pos else RED,
            "day_pnl_sign":  "+" if dpnl_pos else "",
            "div_yield":     x["div_yield"],
        })
    return rows