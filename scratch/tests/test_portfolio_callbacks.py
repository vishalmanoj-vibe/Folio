from typing import Any
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.portfolio_callbacks import register_callbacks


class MockDashApp:
    """Mock Dash application harness to capture and test nested callbacks."""

    def __init__(self) -> None:
        self.callbacks: dict[str, Any] = {}

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.callbacks[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_app() -> MockDashApp:
    """Fixture to initialize register_callbacks and capture functions."""
    app = MockDashApp()
    register_callbacks(app)
    return app


@pytest.fixture
def mock_portfolio_data() -> dict[str, Any]:
    """Strictly typed mock holdings payload matching stats engine requirements."""
    return {
        "fetched_at": "12:00:00",
        "holdings": [
            {
                "ticker": "VAS",
                "ticker_yf": "VAS.AX",
                "total_shares": 10.0,
                "avg_cost": 90.0,
                "last_price": 95.0,
                "day_chg": 0.5,
                "day_chg_pct": 0.53,
                "day_high": 96.0,
                "day_low": 94.0,
                "mkt_value": 950.0,
                "total_cost": 900.0,
                "pnl": 50.0,
                "pnl_pct": 5.56,
                "day_pnl": 5.0,
                "div_yield": 4.5,
                "realized_div": 20.0,
                "div_frequency": "Quarterly",
                "annual_div": 42.75,
            }
        ],
    }


# ── Test update_market_status ──
@patch("callbacks.portfolio_callbacks.market_badge", return_value="mock-market-badge")
def test_update_market_status(mock_badge: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_market_status")
    assert func is not None
    assert func(1, "/") == "mock-market-badge"


# ── Test update_last_refreshed ──
@patch("callbacks.portfolio_callbacks.is_market_open")
def test_update_last_refreshed(mock_open: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_last_refreshed")
    assert func is not None

    # Market open, empty data
    mock_open.return_value = True
    cls, txt = func(None, "/")
    assert cls == "pulse-dot active"
    assert "just now" in txt

    # Market closed, standard data
    mock_open.return_value = False
    cls, txt = func({"fetched_at": "12:34:56"}, "/")
    assert cls == "pulse-dot"
    assert "12:34:56" in txt

    # ISO format datetime
    cls, txt = func({"fetched_at": "2026-06-09T14:45:00"}, "/")
    assert "14:45:00" in txt


# ── Test update_stats ──
def test_update_stats_prioritized_rendering(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None
    result = update_stats_func(mock_portfolio_data, "/watchlist")
    assert result == dash.no_update


def test_update_stats_skeletons_on_missing_data(mock_app: MockDashApp) -> None:
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None
    empty_data: dict[str, Any] = {"holdings": [], "fetched_at": ""}
    result = update_stats_func(empty_data, "/")
    assert isinstance(result, list)
    assert len(result) == 8


def test_update_stats_success(mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]) -> None:
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None
    result = update_stats_func(mock_portfolio_data, "/")
    assert isinstance(result, list)
    assert len(result) == 8
    assert "$950.00" in result[0].children[1].children
    assert "$900.00" in result[1].children[1].children


# ── Test update_live_table ──
def test_update_live_table_off_page(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_live_table")
    assert func is not None
    assert func({}, {}, "/watchlist", "", {}) == dash.no_update


def test_update_live_table_invalid_data(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_live_table")
    assert func is not None
    # Invalid data type
    res = func(None, {}, "/", "", {})
    assert res is not None  # Returns table skeleton

    # Empty holdings list
    res2 = func({"holdings": []}, {}, "/", "", {})
    assert res2 is not None


@patch("data.database.get_connection")
def test_update_live_table_success(
    mock_conn_func: MagicMock, mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    func = mock_app.callbacks.get("update_live_table")
    assert func is not None

    # Mock SQL connection for sentiment query
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [
        {"ticker": "VAS", "sentiment": "Positive", "score": 0.45}
    ]
    mock_conn_func.return_value = mock_conn

    # 1. Test rendering with empty/no filter
    res = func(mock_portfolio_data, {"sort_col": "ticker", "sort_dir": "asc"}, "/", "", {})
    assert res is not None
    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()

    # 2. Test filter query matching
    res_filtered = func(
        mock_portfolio_data, {"sort_col": "ticker", "sort_dir": "asc"}, "/", "vas", {}
    )
    assert res_filtered is not None

    # 3. Test filter query not matching
    res_no_match = func(
        mock_portfolio_data, {"sort_col": "ticker", "sort_dir": "asc"}, "/", "xyz", {}
    )
    # Should say "No positions match your filter"
    assert "No positions match" in res_no_match.children

    # 4. Test signals display in suggestions
    signals_store = {"raw": {"VAS": {"signal": "BUY"}}}
    res_signals = func(
        mock_portfolio_data, {"sort_col": "ticker", "sort_dir": "asc"}, "/", "", signals_store
    )
    assert res_signals is not None
