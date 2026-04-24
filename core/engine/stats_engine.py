"""
core/engine/stats_engine.py
============================
Portfolio statistics and formatting logic.

Extracted from callbacks/portfolio_callbacks.py so callbacks contain
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
        total_day, annual_div, port_yield, realized_div
    """
    total_val  = sum(x["mkt_value"]  for x in holdings)
    total_cost = sum(x["total_cost"] for x in holdings)
    total_pnl  = total_val - total_cost
    pnl_pct    = (total_pnl / total_cost * 100) if total_cost else 0.0
    total_day  = sum(x["day_pnl"]    for x in holdings)
    prev_total = total_val - total_day
    day_pct    = (total_day / prev_total * 100) if prev_total else 0.0

    annual_div = sum(x["annual_div"] for x in holdings)
    realized_div = sum(x.get("realized_div", 0.0) for x in holdings)
    port_yield = (annual_div / total_val * 100) if total_val else 0.0

    return {
        "total_val":    round(total_val,  2),
        "total_cost":   round(total_cost, 2),
        "total_pnl":    round(total_pnl,  2),
        "pnl_pct":      round(pnl_pct,    2),
        "total_day":    round(total_day,  2),
        "day_pct":      round(day_pct,    2),
        "annual_div":   round(annual_div, 2),
        "realized_div": round(realized_div, 2),
        "port_yield":   round(port_yield, 2),
    }


def build_live_table_rows(holdings: list[dict], sort_col: str = "mkt_value", sort_dir: str = "desc") -> list[dict]:
    """
    Sort holdings by any column and attach pre-computed display fields.

    Parameters
    ----------
    holdings : list of enriched holding dicts
    sort_col : str, the key to sort by (e.g. 'ticker', 'mkt_value', 'pnl_pct')
    sort_dir : str, 'asc' or 'desc'

    Returns
    -------
    list of pre-formatted row dicts.
    """
    # ── Sorting logic ─────────────────────────────────────────────────────────
    # Handle cases where the sort_col might be missing or None
    def get_sort_val(x):
        val = x.get(sort_col, 0)
        if val is None: return 0
        if isinstance(val, str): return val.lower()
        return val

    sorted_holdings = sorted(
        holdings, 
        key=get_sort_val, 
        reverse=(sort_dir == "desc")
    )

    rows = []
    for x in sorted_holdings:
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
            "realized_div":  x.get("realized_div", 0.0),
            "div_frequency": x.get("div_frequency", "Unknown"),
            "last_div_amount": x.get("last_div_amount", 0.0),
        })
    return rows