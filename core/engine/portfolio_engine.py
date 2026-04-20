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

def build_holdings(history: list[dict]) -> list[dict]:
    """
    Aggregate raw buy/sell transaction records into one consolidated row
    per ticker that is still held (net shares > 0).

    Validates every transaction before processing; invalid rows are skipped
    with a warning rather than raising so the rest of the portfolio still loads.

    Parameters
    ----------
    history : list of transaction dicts
        Each dict must have: type, ticker, shares, price, date (YYYY-MM-DD).

    Returns
    -------
    list of HoldingDicts — one per held ticker, each containing:
        ticker, ticker_yf, name, market,
        total_shares, total_cost, avg_cost,
        first_purchase, buy_tranches
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

        results.append({
            "ticker":         ticker,
            "ticker_yf":      ticker + ".AX",
            "name":           NAMES.get(ticker, ticker),   # static fallback only
            "market":         "ETF/ASX",
            "total_shares":   net_shares,
            "total_cost":     remaining_cost,
            "avg_cost":       avg_cost,
            "first_purchase": buys["date"].min(),
            "buy_tranches":   build_tranches(ticker, buys),
        })

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

    for tr in buy_tranches:
        buy_date = pd.to_datetime(tr["date"])
        mask = close_series.index >= buy_date
        if not mask.any():
            logger.debug(
                "Tranche %s @ %s: no history on or after buy date",
                tr.get("ticker", "?"), tr["date"],
            )
            continue

        sub   = close_series[mask].copy()
        pnl_s = (sub - tr["price"]) * tr["shares"]
        pct_s = (sub - tr["price"]) / tr["price"] * 100

        result.append({
            "dates":     [d.strftime("%Y-%m-%d %H:%M:%S") if d.hour != 0 or d.minute != 0 else d.strftime("%Y-%m-%d") for d in sub.index],
            "pnl":       [round(v, 2) for v in pnl_s.tolist()],
            "pct":       [round(v, 2) for v in pct_s.tolist()],
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


def compute_portfolio_snapshot(history: list[dict]) -> dict:
    """
    Build a self-contained portfolio snapshot from raw transaction history alone.

    No network calls, no live prices.  Uses existing engine functions only.

    Returns
    -------
    dict with keys:
        holdings    – output of build_holdings(history)
        allocation  – {ticker: pct_of_total_cost}, sums to 100
        pnl_series  – {ticker: [0.0, ...]} one entry per buy tranche (baseline)
        cost_series – {ticker: [running_cost, ...]} cumulative cost per tranche
        metrics     – always {} (live metrics need market data)
    """
    holdings = build_holdings(history)

    if not holdings:
        return {
            "holdings":    [],
            "pnl_series":  {},
            "cost_series": {},
            "allocation":  {},
            "metrics":     {},
        }

    total_cost = sum(h["total_cost"] for h in holdings)
    allocation = (
        {h["ticker"]: round(h["total_cost"] / total_cost * 100, 2) for h in holdings}
        if total_cost > 0 else {}
    )

    pnl_series:  dict[str, list[float]] = {}
    cost_series: dict[str, list[float]] = {}

    for h in holdings:
        tranches = sorted(h["buy_tranches"], key=lambda t: t["date"])
        if not tranches:
            continue
        running_cost = 0.0
        costs, pnls = [], []
        for tr in tranches:
            running_cost += float(tr["shares"]) * float(tr["price"])
            costs.append(round(running_cost, 2))
            pnls.append(0.0)  # P&L at purchase is always 0
        cost_series[h["ticker"]] = costs
        pnl_series[h["ticker"]]  = pnls

    return {
        "holdings":    holdings,
        "pnl_series":  pnl_series,
        "cost_series": cost_series,
        "allocation":  allocation,
        "metrics":     {},
    }