# core/engine/portfolio_engine.py
"""
core/engine/portfolio_engine.py
================================
Portfolio computation engine.

Pure Python — no Dash, no yfinance, no network calls.
All functions are independently testable and importable.

Exported functions
------------------
build_holdings(history)
    Aggregate raw buy/sell transaction records into one holding per ticker.

compute_tranche_pnl(close_series, buy_tranches)
    Day-by-day P&L and % return for each buy tranche from purchase date.

compute_holding_pnl(holding, last_price, prev_close)
    Snapshot market-value and P&L metrics given live price data.

aggregate_shares(buys, sells)
    Low-level helper: return (total_bought, total_cost, total_sold, net_shares).

build_tranches(ticker, buys)
    Low-level helper: convert buy rows into the tranche list format.
"""

from __future__ import annotations

import logging
import pandas as pd

from config.constants import NAMES
from core.validators import validate_transaction

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Holdings aggregation
# ─────────────────────────────────────────────────────────────────────────────

def build_holdings(history: list[dict], include_tranches: bool = True) -> list[dict]:
    """
    Aggregate raw buy/sell transaction records into one consolidated row
    per ticker that is still held (net shares > 0).

    Validates every transaction before processing; invalid rows are skipped
    with a warning rather than raising so the rest of the portfolio still loads.

    Parameters
    ----------
    history : list of transaction dicts
        Each dict must have: type, ticker, shares, price, date (YYYY-MM-DD).
    include_tranches : bool, default True
        If True, includes the full list of buy tranches in each holding.

    Returns
    -------
    list of HoldingDicts — one per held ticker, each containing:
        ticker, ticker_yf, name, market,
        total_shares, total_cost, avg_cost,
        first_purchase, buy_tranches (optional)
    """
    if not history:
        return []

    # ── Validate — skip invalid rows rather than crashing ────────────────────
    invalid: list[tuple[int, str]] = []
    for i, txn in enumerate(history):
        ok, msg = validate_transaction(txn)
        if not ok:
            invalid.append((i, msg))
            logger.warning("Invalid transaction at index %d: %s", i, msg)

    if invalid:
        logger.error("Skipping %d invalid transaction(s)", len(invalid))

    bad_indices = {i for i, _ in invalid}
    valid_history = [t for i, t in enumerate(history) if i not in bad_indices]

    if not valid_history:
        logger.warning("No valid transactions after validation")
        return []

    df = pd.DataFrame(valid_history)
    results: list[dict] = []

    for ticker, grp in df.groupby("ticker"):
        buys  = grp[grp["type"] == "buy"].copy()
        sells = (
            grp[grp["type"] == "sell"].copy()
            if "sell" in grp["type"].values
            else pd.DataFrame()
        )

        if buys.empty:
            continue

        total_bought, total_cost, total_sold, net_shares = aggregate_shares(buys, sells)

        if net_shares <= 0:
            continue   # fully sold — exclude

        avg_cost = round(total_cost / total_bought, 4)
        # Proportional cost: preserves correct cost basis when shares are sold
        remaining_cost = round(total_cost * (net_shares / total_bought), 2)

        holding = {
            "ticker":         ticker,
            "ticker_yf":      ticker + ".AX",
            "name":           NAMES.get(ticker, ticker),   # static fallback only
            "market":         "ETF/ASX",
            "total_shares":   net_shares,
            "total_cost":     remaining_cost,
            "avg_cost":       avg_cost,
            "first_purchase": buys["date"].min(),
        }
        if include_tranches:
            holding["buy_tranches"] = build_tranches(ticker, buys)
        results.append(holding)

    logger.info("Built %d holding(s) from %d transaction(s)", len(results), len(history))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Per-tranche P&L history
# ─────────────────────────────────────────────────────────────────────────────

def compute_tranche_pnl(
    close_series: pd.Series,
    buy_tranches: list[dict],
) -> list[dict]:
    """
    For each buy tranche, compute day-by-day P&L and % return from the
    purchase date onwards.

    Parameters
    ----------
    close_series : pd.Series
        tz-naive DatetimeIndex → float close prices (full history).
    buy_tranches : list of tranche dicts
        Each dict must contain: date (str YYYY-MM-DD), price (float),
        shares (float).

    Returns
    -------
    list of TrancheDict, each containing:
        dates (list[str]), pnl (list[float]), pct (list[float]),
        shares (float), buy_price (float), buy_date (str)
    """
    result: list[dict] = []
    if close_series.empty:
        return result

    has_time = (close_series.index.hour != 0).any() or (close_series.index.minute != 0).any()
    date_fmt = "%Y-%m-%d %H:%M:%S" if has_time else "%Y-%m-%d"

    for tr in buy_tranches:
        buy_date = pd.to_datetime(tr["date"])
        sub = close_series[close_series.index >= buy_date]
        if sub.empty:
            logger.debug(
                "Tranche %s @ %s: no history on or after buy date",
                tr.get("ticker", "?"), tr["date"],
            )
            continue

        pnl_s = (sub - tr["price"]) * tr["shares"]
        pct_s = (sub - tr["price"]) / tr["price"] * 100

        result.append({
            "dates":     sub.index.strftime(date_fmt).tolist(),
            "pnl":       pnl_s.round(2).tolist(),
            "pct":       pct_s.round(2).tolist(),
            "shares":    float(tr["shares"]),
            "buy_price": float(tr["price"]),
            "buy_date":  tr["date"],
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Snapshot P&L for a single holding
# ─────────────────────────────────────────────────────────────────────────────

def compute_holding_pnl(
    holding: dict,
    last_price: float,
    prev_close: float,
) -> dict:
    """
    Compute market value and P&L metrics for one holding given live prices.

    Parameters
    ----------
    holding    : HoldingDict from build_holdings()
    last_price : current / last traded price
    prev_close : previous session's closing price

    Returns
    -------
    dict with keys:
        mkt_value (float), pnl (float), pnl_pct (float),
        day_chg (float), day_chg_pct (float), day_pnl (float)
    """
    shares = holding["total_shares"]
    cost   = holding["total_cost"]

    mkt_value   = round(shares * last_price, 2)
    pnl         = round(mkt_value - cost, 2)
    pnl_pct     = round((pnl / cost * 100) if cost else 0, 2)

    day_chg     = round(last_price - prev_close, 4)
    day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)
    day_pnl     = round(day_chg * shares, 2)

    return {
        "mkt_value":   mkt_value,
        "pnl":         pnl,
        "pnl_pct":     pnl_pct,
        "day_chg":     day_chg,
        "day_chg_pct": day_chg_pct,
        "day_pnl":     day_pnl,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private / low-level helpers (exported for testing)
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_shares(
    buys: pd.DataFrame,
    sells: pd.DataFrame,
) -> tuple[float, float, float, float]:
    """
    Summarise buy and sell DataFrames into scalar totals.

    Returns
    -------
    (total_bought, total_cost, total_sold, net_shares)
    """
    total_bought = float(buys["shares"].sum())
    total_cost   = float((buys["shares"] * buys["price"]).sum())
    total_sold   = float(sells["shares"].sum()) if not sells.empty else 0.0
    net_shares   = total_bought - total_sold
    return total_bought, total_cost, total_sold, net_shares


def build_tranches(ticker: str, buys: pd.DataFrame) -> list[dict]:
    """
    Convert buy rows into the tranche list consumed by chart callbacks.

    Each tranche carries both canonical keys (date, price, shares) and
    legacy aliases (buy_date, buy_price) that chart_callbacks.py expects.
    """
    return [
        {
            "ticker":    ticker,
            "shares":    float(r["shares"]),
            "price":     float(r["price"]),
            "date":      str(r["date"]),
            "buy_price": float(r["price"]),   # alias — chart compat
            "buy_date":  str(r["date"]),       # alias — chart compat
        }
        for _, r in buys.iterrows()
    ]

