# scratch/tests/test_intelligence_service.py
import math
import os
import sqlite3
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from data.database import init_db
from services.intelligence_service import (
    _get_cached_metadata,
    _save_metadata,
    _symbol_to_region,
    _truncate_dict,
    annualised_volatility,
    compute_risk_metrics,
    compute_smart_alerts,
    drawdown_series,
    fetch_etf_geo_weights,
    fetch_etf_sector_weights,
    geo_exposure,
    get_exposure_detail,
    max_drawdown,
    per_ticker_volatility,
    portfolio_returns,
    sector_exposure,
    sharpe_ratio,
)

# ── Cache Clearing Fixture ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_in_memory_cache() -> Generator[None, None, None]:
    """Clears the global core in-memory cache to prevent test pollution."""
    from core.cache import _CACHE

    _CACHE.clear()
    yield
    _CACHE.clear()


# ── Isolated Database Fixture ──────────────────────────────────────────────────


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


# ── Basic Utility Tests ──────────────────────────────────────────────────────


def test_symbol_to_region():
    assert _symbol_to_region("VAS.AX") == "Australia"
    assert _symbol_to_region("A200.XA") == "Australia"
    assert _symbol_to_region("AAPL") == "USA"
    assert _symbol_to_region("VGS.NZ") == "New Zealand"
    assert _symbol_to_region("RY.TO") == "Canada"
    assert _symbol_to_region("BP.L") == "United Kingdom"
    assert _symbol_to_region("TEST.ST") == "Sweden"
    assert _symbol_to_region("TEST.UNKNOWN") == "Other"


def test_truncate_dict():
    # Empty dictionary
    assert _truncate_dict({}) == {}

    # Dictionary size less than top_n
    small_dict = {"A": 0.5, "B": 0.5}
    assert _truncate_dict(small_dict, top_n=5) == small_dict

    # Dictionary size larger than top_n
    large_dict = {f"k{i}": 0.05 for i in range(20)}
    truncated = _truncate_dict(large_dict, top_n=10)
    assert len(truncated) == 11  # 10 items + "Other Holdings"
    assert "Other Holdings" in truncated
    # 10 items kept, remaining 10 summed (10 * 0.05 = 0.50)
    assert math.isclose(truncated["Other Holdings"], 0.50, abs_tol=0.01)

    # Dictionary size larger than top_n containing 'Other'
    large_dict_other = {f"k{i}": 0.05 for i in range(20)}
    large_dict_other["Other"] = 0.10
    truncated_other = _truncate_dict(large_dict_other, top_n=10)
    assert "Other" in truncated_other
    # Ensure remaining weights got aggregated into existing 'Other'
    assert truncated_other["Other"] > 0.10


# ── Metadata DB Caching Tests ────────────────────────────────────────────────


def test_save_and_get_cached_metadata():
    # Verify metadata saves and loads correctly
    data = {"Technology": 60.0, "Financials": 40.0}
    _save_metadata("VAS.AX", "sector", data)

    cached = _get_cached_metadata("VAS.AX", "sector")
    assert cached is not None
    assert cached["Technology"] == 60.0
    assert cached["Financials"] == 40.0

    # Non-existent entry returns None
    assert _get_cached_metadata("VGS.AX", "sector") is None

    # Stale checks: Directly update the DB row to make it 10 days old
    from data.database import get_connection

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE etf_metadata SET updated_at = datetime('now', '-10 days') WHERE ticker = 'VAS.AX'"
        )
        conn.commit()
    finally:
        conn.close()

    assert _get_cached_metadata("VAS.AX", "sector") is None


# ── ETF Allocation Scrapers Tests ────────────────────────────────────────────


@patch("services.intelligence_service.get_ticker_cached")
def test_fetch_etf_sector_weights_yfinance(mock_get_ticker):
    # Mock yfinance ticker
    mock_ticker = MagicMock()
    mock_ticker.funds_data = MagicMock()
    # Return mock sector weightings
    mock_ticker.funds_data.sector_weightings = {
        "technology": 0.60,
        "financial-services": 0.40,
    }
    mock_get_ticker.return_value = mock_ticker

    # Sector weights should be fetched, rounded, and cached in DB
    weights = fetch_etf_sector_weights("VAS.AX")
    assert weights["Technology"] == 60.0
    assert weights["Financials"] == 40.0

    # Verify persistent save occurred
    assert _get_cached_metadata("VAS.AX", "sector") is not None


@patch("services.intelligence_service.get_ticker_cached")
def test_fetch_etf_geo_weights_yfinance(mock_get_ticker):
    # Mock yfinance regional exposure
    mock_ticker = MagicMock()
    mock_ticker.funds_data = MagicMock()
    mock_ticker.funds_data.regional_exposure = {
        "North America": 0.70,
        "Europe Dev": 0.30,
    }
    mock_get_ticker.return_value = mock_ticker

    weights = fetch_etf_geo_weights("VGS.AX")
    assert weights["North America"] == 70.0
    assert weights["Europe Dev"] == 30.0


# ── Risk Metric Mathematics Tests ───────────────────────────────────────────


def test_portfolio_returns():
    # Feed simple histories and holdings
    histories = {
        "VAS": [
            {"Date": "2026-01-01", "Close": 100.0},
            {"Date": "2026-01-02", "Close": 101.0},  # +1%
            {"Date": "2026-01-03", "Close": 102.01},  # +1%
        ],
        "VGS": [
            {"Date": "2026-01-01", "Close": 50.0},
            {"Date": "2026-01-02", "Close": 49.0},  # -2%
            {"Date": "2026-01-03", "Close": 48.02},  # -2%
        ],
    }
    holdings = [
        {"ticker": "VAS", "mkt_value": 500.0},  # 50%
        {"ticker": "VGS", "mkt_value": 500.0},  # 50%
    ]

    p_returns = portfolio_returns(histories, holdings)
    # Weighted returns: 50% * 1% + 50% * -2% = -0.5% each day
    assert len(p_returns) == 2
    assert math.isclose(p_returns.iloc[0], -0.005, abs_tol=0.0001)
    assert math.isclose(p_returns.iloc[1], -0.005, abs_tol=0.0001)


def test_annualised_volatility():
    # Static daily returns
    returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01])
    vol = annualised_volatility(returns)
    # Volatility should be round(std_dev * sqrt(252) * 100, 2)
    expected = round(returns.std() * math.sqrt(252) * 100, 2)
    assert vol == expected

    # Edge cases
    assert math.isnan(annualised_volatility(pd.Series(dtype=float)))
    assert math.isnan(annualised_volatility(pd.Series([0.01])))


def test_sharpe_ratio():
    # 5 matching returns to satisfy min length check
    returns = pd.Series([0.005, 0.006, 0.004, 0.005, 0.006])
    sr = sharpe_ratio(returns)
    assert sr > 0.0

    # Edge cases
    assert math.isnan(sharpe_ratio(pd.Series(dtype=float)))
    assert math.isnan(sharpe_ratio(pd.Series([0.01])))


def test_max_drawdown():
    returns = pd.Series([0.0, -0.05, -0.10, 0.05, 0.10])
    dd = max_drawdown(returns)
    # Peak at 1.0, drops to (1.0 * 0.95 * 0.90) = 0.855 -> max drawdown is -14.5%
    assert dd < 0
    assert math.isclose(dd, -14.5, abs_tol=0.1)


def test_drawdown_series():
    returns = pd.Series([0.0, -0.05, 0.10])
    dds = drawdown_series(returns)
    assert dds.iloc[0] == 0.0
    assert dds.iloc[1] == -5.0
    assert dds.iloc[2] == 0.0


def test_per_ticker_volatility():
    histories = {
        "VAS": [
            {"Date": "2026-01-01", "Close": 100.0},
            {"Date": "2026-01-02", "Close": 101.0},
            {"Date": "2026-01-03", "Close": 99.0},
            {"Date": "2026-01-04", "Close": 102.0},
            {"Date": "2026-01-05", "Close": 100.0},
            {"Date": "2026-01-06", "Close": 101.0},
        ]
    }
    vols = per_ticker_volatility(histories)
    assert "VAS" in vols
    assert isinstance(vols["VAS"], float)


def test_compute_risk_metrics():
    # Verify risk metrics returns full set of expected keys
    port_data = {
        "holdings": [{"ticker": "VAS", "mkt_value": 100.0}],
        "histories": {
            "VAS": [
                {"Date": "2026-01-01", "Close": 100.0},
                {"Date": "2026-01-02", "Close": 101.0},
                {"Date": "2026-01-03", "Close": 100.0},
                {"Date": "2026-01-04", "Close": 102.0},
                {"Date": "2026-01-05", "Close": 100.0},
                {"Date": "2026-01-06", "Close": 101.0},
            ]
        },
    }
    metrics = compute_risk_metrics(port_data, period="max")
    assert "vol" in metrics
    assert "sharpe" in metrics
    assert "max_dd" in metrics
    assert "current_dd" in metrics
    assert len(metrics["dd_dates"]) > 0


# ── Exposure Aggregations & Details Tests ────────────────────────────────────


def test_exposures_grouping():
    # Setup database cache to bypass network
    _save_metadata("VAS.AX", "sector", {"Technology": 80.0, "Financials": 20.0})
    _save_metadata("VGS.AX", "sector", {"Healthcare": 50.0, "Technology": 50.0})

    port_data = {
        "holdings": [
            {"ticker": "VAS", "ticker_yf": "VAS.AX", "mkt_value": 500.0},
            {"ticker": "VGS", "ticker_yf": "VGS.AX", "mkt_value": 500.0},
        ]
    }

    # Blended sector weights:
    # VAS is 50%, VGS is 50%
    # Technology: 50% * 80 + 50% * 50 = 65%
    # Financials: 50% * 20 = 10%
    # Healthcare: 50% * 50 = 25%
    sectors = sector_exposure(port_data)
    assert sectors["Technology"] == 65.0
    assert sectors["Healthcare"] == 25.0
    assert sectors["Financials"] == 10.0


def test_get_exposure_detail():
    _save_metadata("VAS.AX", "sector", {"Technology": 80.0, "Financials": 20.0})
    _save_metadata("VGS.AX", "sector", {"Healthcare": 50.0, "Technology": 50.0})

    port_data = {
        "holdings": [
            {"ticker": "VAS", "ticker_yf": "VAS.AX", "mkt_value": 600.0},  # 60%
            {"ticker": "VGS", "ticker_yf": "VGS.AX", "mkt_value": 400.0},  # 40%
        ]
    }

    # Contribution to Technology:
    # VAS: 60% * 80 = 48.0
    # VGS: 40% * 50 = 20.0
    detail = get_exposure_detail(port_data, "sector", "Technology")
    assert len(detail) == 2
    assert detail[0]["ticker"] == "VAS"
    assert detail[0]["weight"] == 48.0
    assert detail[1]["ticker"] == "VGS"
    assert detail[1]["weight"] == 20.0


# ── Smart Alert Verification Tests ───────────────────────────────────────────


def test_compute_smart_alerts():
    # Set thresholds
    metrics = {
        "vol": 25.0,  # Exceeds THRESHOLDS["high_vol_annualised"] (20.0)
        "sharpe": 0.3,  # Below THRESHOLDS["low_sharpe"] (0.5)
        "current_dd": -20.0,  # Exceeds THRESHOLDS["bad_drawdown"] (-15)
    }

    port_data = {
        "holdings": [
            {
                "ticker": "VAS",
                "ticker_yf": "VAS.AX",
                "mkt_value": 900.0,
            },  # 90% (exceeds single_etf_weight 40%)
            {"ticker": "VGS", "ticker_yf": "VGS.AX", "mkt_value": 100.0},
        ]
    }

    # Setup database metadata caches to avoid scraper triggers
    _save_metadata(
        "VAS.AX", "sector", {"Technology": 50.0, "Financials": 50.0}
    )  # 50% Technology in VAS -> blended Tech = 45% (exceeds tech_overweight 35%)
    _save_metadata("VGS.AX", "sector", {"Healthcare": 100.0})

    _save_metadata(
        "VAS.AX", "geo", {"Australia": 100.0}
    )  # 100% Australia in VAS -> blended Australia = 90% (exceeds geo_overweight 60%)
    _save_metadata("VGS.AX", "geo", {"USA": 100.0})

    alerts = compute_smart_alerts(metrics, port_data)

    alert_titles = [a["title"] for a in alerts]
    assert any("VAS is 90.0% of your portfolio" in t for t in alert_titles)
    assert any("Overweight Financials" in t or "Overweight Technology" in t for t in alert_titles)
    assert any("Heavy Australia exposure" in t for t in alert_titles)
    assert any("Elevated Volatility" in t for t in alert_titles)
    assert any("Low Sharpe Ratio" in t for t in alert_titles)
    assert any("Portfolio in drawdown" in t for t in alert_titles)
