# scratch/tests/test_portfolio_engine.py
import math

import pandas as pd
import pytest

from core.engine.portfolio_engine import (
    aggregate_shares,
    build_holdings,
    build_tranches,
    compute_holding_pnl,
    compute_tranche_pnl,
)


def test_build_holdings_empty():
    assert build_holdings([]) == []
    assert build_holdings(None) == []


def test_build_holdings_invalid():
    # Invalid transaction record (negative shares) should be skipped
    history = [
        {"type": "buy", "ticker": "VAS", "shares": -10.0, "price": 90.0, "date": "2026-01-01"},
        {"type": "buy", "ticker": "VGS", "shares": 5.0, "price": 100.0, "date": "2026-01-02"},
    ]
    holdings = build_holdings(history)
    # Only VGS should be built
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "VGS"
    assert holdings[0]["total_shares"] == 5.0


def test_build_holdings_buy_only():
    history = [
        {"type": "buy", "ticker": "VAS", "shares": 10.0, "price": 90.0, "date": "2026-01-01"},
        {"type": "buy", "ticker": "VAS", "shares": 5.0, "price": 96.0, "date": "2026-01-02"},
    ]
    holdings = build_holdings(history, include_tranches=True)
    assert len(holdings) == 1
    vas = holdings[0]
    assert vas["ticker"] == "VAS"
    assert vas["total_shares"] == 15.0
    # Average cost = ((10 * 90) + (5 * 96)) / 15 = (900 + 480) / 15 = 92.0
    assert vas["avg_cost"] == 92.0
    assert vas["total_cost"] == 1380.0
    assert len(vas["buy_tranches"]) == 2
    assert vas["buy_tranches"][0]["shares"] == 10.0
    assert vas["buy_tranches"][1]["shares"] == 5.0


def test_build_holdings_with_sells():
    # Tests that sells are aggregated and net shares / proportional remaining cost is computed.
    # Note: portfolio_engine.py uses buys-sells aggregation:
    # total_bought, total_cost, total_sold, net_shares = aggregate_shares(buys, sells)
    # remaining_cost = total_cost * (net_shares / total_bought)
    # Let's verify this formula behavior:
    history = [
        {"type": "buy", "ticker": "VAS", "shares": 10.0, "price": 90.0, "date": "2026-01-01"},
        {"type": "buy", "ticker": "VAS", "shares": 10.0, "price": 100.0, "date": "2026-01-02"},
        {"type": "sell", "ticker": "VAS", "shares": 5.0, "price": 105.0, "date": "2026-01-03"},
    ]
    holdings = build_holdings(history, include_tranches=False)
    assert len(holdings) == 1
    vas = holdings[0]
    assert vas["total_shares"] == 15.0
    # total_bought = 20, total_cost = 1900
    # remaining_cost = 1900 * (15/20) = 1425.0
    assert vas["total_cost"] == 1425.0
    assert vas["avg_cost"] == 95.0  # 1900 / 20

    # Fully sold out position should be excluded
    history_fully_sold = [
        {"type": "buy", "ticker": "VAS", "shares": 10.0, "price": 90.0, "date": "2026-01-01"},
        {"type": "sell", "ticker": "VAS", "shares": 10.0, "price": 95.0, "date": "2026-01-02"},
    ]
    assert build_holdings(history_fully_sold) == []


def test_compute_tranche_pnl():
    # Build close series with date index
    idx = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])
    close_series = pd.Series([100.0, 102.0, 105.0], index=idx)

    buy_tranches = [
        {"ticker": "VAS", "shares": 10.0, "price": 100.0, "date": "2026-01-01"},
        {"ticker": "VAS", "shares": 5.0, "price": 101.0, "date": "2026-01-02"},
    ]

    pnl_results = compute_tranche_pnl(close_series, buy_tranches)
    assert len(pnl_results) == 2

    # Tranche 1: purchased Jan 1 @ 100. Shares = 10.
    # Returns from Jan 1 onwards: [Jan 1, Jan 2, Jan 3]
    # Price difference: [0, 2, 5]
    # P&L: [0 * 10, 2 * 10, 5 * 10] = [0.0, 20.0, 50.0]
    # Pct: [0%, 2%, 5%]
    t1 = pnl_results[0]
    assert t1["buy_price"] == 100.0
    assert t1["dates"] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert t1["pnl"] == [0.0, 20.0, 50.0]
    assert t1["pct"] == [0.0, 2.0, 5.0]

    # Tranche 2: purchased Jan 2 @ 101. Shares = 5.
    # Returns from Jan 2 onwards: [Jan 2, Jan 3]
    # Price difference: [102-101, 105-101] = [1, 4]
    # P&L: [1 * 5, 4 * 5] = [5.0, 20.0]
    # Pct: [1/101 * 100, 4/101 * 100] = [0.99, 3.96]
    t2 = pnl_results[1]
    assert t2["buy_price"] == 101.0
    assert t2["dates"] == ["2026-01-02", "2026-01-03"]
    assert t2["pnl"] == [5.0, 20.0]
    assert math.isclose(t2["pct"][0], 0.99, abs_tol=0.01)
    assert math.isclose(t2["pct"][1], 3.96, abs_tol=0.01)


def test_compute_tranche_pnl_empty():
    assert (
        compute_tranche_pnl(
            pd.Series(dtype=float), [{"date": "2026-01-01", "price": 10.0, "shares": 5}]
        )
        == []
    )

    # Tranche after history range
    idx = pd.to_datetime(["2026-01-01", "2026-01-02"])
    close_series = pd.Series([100.0, 102.0], index=idx)
    buy_tranches = [{"date": "2026-01-03", "price": 105.0, "shares": 5}]
    assert compute_tranche_pnl(close_series, buy_tranches) == []


def test_compute_holding_pnl():
    holding = {
        "ticker": "VAS",
        "total_shares": 10.0,
        "total_cost": 900.0,
        "avg_cost": 90.0,
    }

    # last_price = 95.0, prev_close = 94.0
    # mkt_value = 950.0
    # pnl = 950.0 - 900.0 = 50.0
    # pnl_pct = 50.0 / 900.0 * 100 = 5.56%
    # day_chg = 95.0 - 94.0 = 1.0
    # day_chg_pct = 1.0 / 94.0 * 100 = 1.06%
    # day_pnl = 1.0 * 10 = 10.0
    pnl_metrics = compute_holding_pnl(holding, last_price=95.0, prev_close=94.0)
    assert pnl_metrics["mkt_value"] == 950.0
    assert pnl_metrics["pnl"] == 50.0
    assert math.isclose(pnl_metrics["pnl_pct"], 5.56, abs_tol=0.01)
    assert pnl_metrics["day_chg"] == 1.0
    assert math.isclose(pnl_metrics["day_chg_pct"], 1.06, abs_tol=0.01)
    assert pnl_metrics["day_pnl"] == 10.0


def test_compute_holding_pnl_zero_cost():
    # Avoid division-by-zero error if total_cost or prev_close is zero
    holding = {
        "ticker": "VAS",
        "total_shares": 10.0,
        "total_cost": 0.0,
        "avg_cost": 0.0,
    }
    pnl_metrics = compute_holding_pnl(holding, last_price=95.0, prev_close=0.0)
    assert pnl_metrics["pnl_pct"] == 0.0
    assert pnl_metrics["day_chg_pct"] == 0.0


def test_aggregate_shares_helper():
    buys = pd.DataFrame([{"shares": 10.0, "price": 90.0}, {"shares": 5.0, "price": 96.0}])
    sells = pd.DataFrame([{"shares": 3.0}])

    total_bought, total_cost, total_sold, net_shares = aggregate_shares(buys, sells)
    assert total_bought == 15.0
    assert total_cost == 1380.0
    assert total_sold == 3.0
    assert net_shares == 12.0


def test_build_tranches_helper():
    buys = pd.DataFrame(
        [
            {"shares": 10.0, "price": 90.0, "date": "2026-01-01"},
            {"shares": 5.0, "price": 96.0, "date": "2026-01-02"},
        ]
    )
    tranches = build_tranches("VAS", buys)
    assert len(tranches) == 2
    assert tranches[0]["ticker"] == "VAS"
    assert tranches[0]["shares"] == 10.0
    assert tranches[0]["price"] == 90.0
    assert tranches[0]["buy_price"] == 90.0
    assert tranches[0]["buy_date"] == "2026-01-01"
