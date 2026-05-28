from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.market.dividend_service import (
    calculate_portfolio_dividend_stats,
    get_ticker_dividend_data,
)


@pytest.fixture
def mock_history_data() -> list[dict[str, Any]]:
    """Strictly typed mock SQLite history records with dividends."""
    return [
        {"Date": "2026-03-15 00:00:00", "Close": 100.0, "Dividends": 0.5},
        {"Date": "2026-04-15 00:00:00", "Close": 102.0, "Dividends": 0.0},
        {"Date": "2026-05-15 00:00:00", "Close": 105.0, "Dividends": 0.8},
    ]


@pytest.fixture
def mock_holdings() -> list[dict[str, Any]]:
    """Strictly typed mock holdings payload with transaction tranches."""
    return [
        {
            "ticker": "VHY",
            "ticker_yf": "VHY.AX",
            "total_shares": 100.0,
            "mkt_value": 10500.0,
            "annual_div": 520.0,
            "last_div_amount": 0.8,
            "last_div_date": "2026-05-15",
            "payout_date": "2026-06-01",
            "next_div_date": None,
            "div_frequency": "Quarterly",
            "buy_tranches": [
                {"date": "2026-01-01", "shares": 60.0, "price": 95.0},
                {"date": "2026-04-01", "shares": 40.0, "price": 100.0},
            ],
        }
    ]


@patch("services.market.dividend_service.get_cache")
@patch("services.market.dividend_service.set_cache")
@patch("data.repository.HistoryRepository.load_history")
def test_get_ticker_dividend_data_success(
    mock_load: MagicMock,
    mock_set: MagicMock,
    mock_get: MagicMock,
    mock_history_data: list[dict[str, Any]],
) -> None:
    """Assert dividend retrieval successfully filters, formats, and caches results."""
    mock_get.return_value = None
    mock_load.return_value = mock_history_data

    df: pd.DataFrame = get_ticker_dividend_data("VHY", "VHY.AX")

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) == 2  # Only 2 rows have Dividends > 0
    assert "pay_date" in df.columns
    # Check that confirmed pay dates mapping works for VHY ex-date 2026-04-01
    mock_set.assert_called_once()


@patch("services.market.dividend_service.get_cache")
@patch("services.market.dividend_service.get_ticker_dividend_data")
def test_calculate_portfolio_dividend_stats(
    mock_get_div: MagicMock,
    mock_get_cache: MagicMock,
    mock_holdings: list[dict[str, Any]],
) -> None:
    """Assert portfolio aggregate stats accurately execute tranche eligibility calculations."""
    mock_get_cache.return_value = None
    # Mock VHY dividend history
    mock_get_div.return_value = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-05-15"),
                "pay_date": "2026-06-01",
                "ticker": "VHY",
                "amount": 0.8,
            },
            {
                "date": pd.Timestamp("2026-03-15"),
                "pay_date": "2026-04-05",
                "ticker": "VHY",
                "amount": 0.5,
            },
        ]
    )

    df, stats, events = calculate_portfolio_dividend_stats(mock_holdings)

    # 1. Tranche Eligibility asserts:
    # - On 2026-03-15 ex-date: only 60 shares are eligible (bought 2026-01-01)
    # - On 2026-05-15 ex-date: all 100 shares are eligible (bought 2026-01-01 + 2026-04-01)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # 2. Check total payout calculations
    row_may = df[df["date"] == pd.Timestamp("2026-05-15")].iloc[0]
    row_march = df[df["date"] == pd.Timestamp("2026-03-15")].iloc[0]

    assert row_may["total"] == 0.8 * 100.0  # $80 payout
    assert row_march["total"] == 0.5 * 60.0  # $30 payout

    # 3. KPI stats assertions
    assert stats["annual_income"] == 520.0
    assert stats["portfolio_yield"] == (520.0 / 10500.0) * 100
    assert stats["total_realized"] == 110.0  # $80 + $30

    # 4. Calendar events assertions
    assert len(events) > 0
    assert any(e["type"] == "PAYMENT" for e in events)
