# scratch/tests/test_data_fetcher.py
import math
import os
import sqlite3
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.database import init_db
from services.market.data_fetcher import (
    _calculate_realized_dividends,
    _compute_dividends_bulk,
    _deduce_frequency,
    _extract_col,
    extract_close,
    extract_dividends,
    fetch_benchmarks,
    fetch_live,
    get_etf_name,
    load_portfolio_snapshot,
)


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Redirects database writes to a temporary test DB path."""
    test_db_path = "scratch/tests/test_portfolio.db"

    # Pre-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    with (
        patch("data.database.DB_PATH", test_db_path),
        patch("data.database._DB_INITIALIZED", False),
    ):
        init_db()  # Initialize schema
        yield

    # Post-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


# ── Column Extraction Tests ──────────────────────────────────────────────────


def test_extract_col_single_index():
    df = pd.DataFrame({"Close": [10.0, 11.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    res = _extract_col(df, "VAS.AX", "Close")
    assert len(res) == 2
    assert res.iloc[0] == 10.0


def test_extract_col_multi_index():
    cols = pd.MultiIndex.from_tuples([("VAS.AX", "Close"), ("VGS.AX", "Close")])
    df = pd.DataFrame(
        [[10.0, 50.0], [11.0, 51.0]],
        columns=cols,
        index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
    )

    res = extract_close(df, "VAS.AX")
    assert len(res) == 2
    assert res.iloc[0] == 10.0

    res_missing = _extract_col(df, "NONEXISTENT", "Close")
    assert res_missing.empty


# ── Dividend Frequency Deduction Tests ────────────────────────────────────────


def test_deduce_frequency():
    # Monthly (median ~30 days)
    dates = pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"])
    div_s = pd.Series([0.1, 0.1, 0.1], index=dates)
    assert _deduce_frequency(div_s) == "Monthly"

    # Quarterly (median ~90 days)
    dates = pd.to_datetime(["2026-01-01", "2026-04-01", "2026-07-01"])
    div_s = pd.Series([0.5, 0.5, 0.5], index=dates)
    assert _deduce_frequency(div_s) == "Quarterly"

    # Semi-Annual (median ~180 days)
    dates = pd.to_datetime(["2026-01-01", "2026-07-01", "2027-01-01"])
    div_s = pd.Series([1.0, 1.0, 1.0], index=dates)
    assert _deduce_frequency(div_s) == "Semi-Annual"

    # Annual (median ~365 days)
    dates = pd.to_datetime(["2026-01-01", "2027-01-01"])
    div_s = pd.Series([2.0, 2.0], index=dates)
    assert _deduce_frequency(div_s) == "Annual"

    # Irregular / Empty
    assert _deduce_frequency(pd.Series(dtype=float)) == "Unknown"


# ── Realized Dividends Math Tests ─────────────────────────────────────────────


def test_calculate_realized_dividends():
    dates = pd.to_datetime(["2026-01-15", "2026-04-15"])
    div_s = pd.Series([0.5, 0.6], index=dates)

    # Tranche purchased BEFORE Jan 15 (Jan 1) -> eligible for both
    # Tranche purchased AFTER Jan 15 (Feb 1) -> eligible for second only
    tranches = [
        {"shares": 10.0, "date": "2026-01-01"},
        {"shares": 5.0, "date": "2026-02-01"},
    ]

    # Jan 15 payment: 10 shares * 0.5 = $5.00
    # Apr 15 payment: 15 shares * 0.6 = $9.00
    # Total expected: $14.00
    realized = _calculate_realized_dividends(div_s, tranches)
    assert realized == 14.00


def test_compute_dividends_bulk():
    dates = pd.to_datetime(["2026-01-15"])
    div_s = pd.Series([0.5], index=dates)

    annual, total, yld = _compute_dividends_bulk(div_s, total_shares=10, mkt_value=100.0)
    # 10 shares * 0.5 = 5.00
    assert annual == 5.00
    assert total == 5.00
    assert yld == 5.00


# ── ETF Name Resolution Cache Tests ───────────────────────────────────────────


@patch("services.market.data_fetcher.get_ticker_cached")
def test_get_etf_name_flow(mock_get_ticker):
    # Setup mock ticker
    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "Vanguard Australian Shares ETF"}
    mock_get_ticker.return_value = mock_ticker

    # First fetch: should call yfinance and store in DB
    name1 = get_etf_name("VAS")
    assert name1 == "Vanguard Australian Shares ETF"

    # Verify persistent assets table has it
    from data.repository import PortfolioRepository

    asset = PortfolioRepository().get_asset("VAS")
    assert asset is not None
    assert asset["name"] == "Vanguard Australian Shares ETF"

    # Second fetch: should hit cached asset and not call yfinance
    mock_get_ticker.reset_mock()
    name2 = get_etf_name("VAS")
    assert name2 == "Vanguard Australian Shares ETF"
    mock_get_ticker.assert_not_called()


# ── Load Portfolio Snapshot Tests ─────────────────────────────────────────────


def test_load_portfolio_snapshot_empty():
    res = load_portfolio_snapshot([])
    assert res["holdings"] == []


def test_load_portfolio_snapshot_merge():
    initial_holdings = [
        {"ticker": "VAS", "avg_cost": 90.0, "total_shares": 10.0, "total_cost": 900.0}
    ]

    # Save daily history to repository, which provides prev_close and last_price
    # Insert 2 records: one for latest, one for previous close
    from data.repository import HistoryRepository

    HistoryRepository().save_history(
        "VAS",
        [
            {
                "date": "2026-06-07",
                "open": 94.0,
                "high": 94.0,
                "low": 94.0,
                "close": 94.0,
                "volume": 100,
                "dividends": 0.0,
            },
            {
                "date": "2026-06-08",
                "open": 95.0,
                "high": 95.0,
                "low": 95.0,
                "close": 95.0,
                "volume": 100,
                "dividends": 0.0,
            },
        ],
        period="max",
    )

    # Insert mock snapshot prices into DB
    from data.cache_manager import save_live_prices

    save_live_prices(
        [
            {
                "ticker": "VAS",
                "last_price": 95.0,
                "mkt_value": 950.0,
                "pnl": 50.0,
                "pnl_pct": 5.56,
                "fetched_at": "2026-06-09T12:00:00",
            }
        ]
    )

    snapshot = load_portfolio_snapshot(initial_holdings)
    assert len(snapshot["holdings"]) == 1
    vas = snapshot["holdings"][0]
    assert vas["last_price"] == 95.0
    assert vas["prev_close"] == 94.0
    assert vas["mkt_value"] == 950.0
    assert vas["pnl"] == 50.0


# ── Benchmark Fetching Tests ──────────────────────────────────────────────────


@patch("services.market.data_fetcher._download_with_retry")
def test_fetch_benchmarks(mock_download):
    # Setup mock dataframe returned by download
    cols = pd.MultiIndex.from_tuples([("^GSPC", "Close"), ("^AXJO", "Close")])
    mock_df = pd.DataFrame(
        [[5000.0, 8000.0]],
        columns=cols,
        index=pd.to_datetime(["2026-06-09"]),
    )
    mock_download.return_value = mock_df

    bench = fetch_benchmarks(period="max")
    assert "S&P 500" in bench
    assert "ASX 200" in bench
    assert bench["S&P 500"][0]["Close"] == 5000.0
    assert bench["ASX 200"][0]["Close"] == 8000.0


# ── fetch_live Integration Test ──────────────────────────────────────────────


@patch("services.market.data_fetcher._download_with_retry")
@patch("services.market.data_fetcher.get_etf_name")
def test_fetch_live_success(mock_get_name, mock_download):
    mock_get_name.return_value = "Vanguard Australian Shares ETF"

    # Create mock MultiIndex DataFrame for multi_live (5d)
    cols = pd.MultiIndex.from_tuples(
        [
            ("VAS.AX", "Open"),
            ("VAS.AX", "High"),
            ("VAS.AX", "Low"),
            ("VAS.AX", "Close"),
            ("VAS.AX", "Volume"),
        ]
    )
    now_syd = pd.Timestamp.now(tz="Australia/Sydney")
    mock_live_df = pd.DataFrame([[94.0, 96.0, 93.0, 95.0, 1000]], columns=cols, index=[now_syd])
    mock_download.return_value = mock_live_df

    # Insert a non-stale meta row for VAS so it doesn't trigger 'max' download
    from data.repository import HistoryRepository

    repo_hist = HistoryRepository()
    repo_hist.save_history(
        "VAS",
        [
            {
                "date": "2026-06-08",
                "close": 94.0,
                "open": 94.0,
                "high": 94.0,
                "low": 94.0,
                "volume": 100,
                "dividends": 0.0,
            }
        ],
        period="max",
    )

    holdings = [
        {
            "ticker": "VAS",
            "ticker_yf": "VAS.AX",
            "total_shares": 10.0,
            "total_cost": 900.0,
            "avg_cost": 90.0,
        }
    ]

    res, _, sig = fetch_live(holdings, record_snapshots=False)

    assert "holdings" in res
    assert len(res["holdings"]) == 1
    vas = res["holdings"][0]
    assert vas["last_price"] == 95.0
    assert vas["mkt_value"] == 950.0
    assert vas["pnl"] == 50.0
