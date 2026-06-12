from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import dash
import pytest

from callbacks.transaction_callbacks import register_callbacks


class MockDashApp:
    def __init__(self) -> None:
        self.callbacks: dict[str, Any] = {}

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.callbacks[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_app() -> MockDashApp:
    app = MockDashApp()
    register_callbacks(app)
    return app


def test_discover_ticker_empty(mock_app: MockDashApp) -> None:
    discover_func = mock_app.callbacks.get("discover_ticker")
    assert discover_func is not None

    # Empty inputs
    assert discover_func("") == ("", dash.no_update)
    assert discover_func("   ") == ("", dash.no_update)
    assert discover_func("A") == ("", dash.no_update)


@patch(
    "callbacks.transaction_callbacks.get_etf_name", return_value="Vanguard Australian Shares ETF"
)
@patch("callbacks.transaction_callbacks.get_connection")
def test_discover_ticker_success_db(
    mock_conn_func: MagicMock, mock_get_etf_name: MagicMock, mock_app: MockDashApp
) -> None:
    discover_func = mock_app.callbacks.get("discover_ticker")
    assert discover_func is not None

    # Set up mock DB connection returning a price
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"last_price": 95.50}
    mock_conn_func.return_value = mock_conn

    name, price = discover_func("VAS")
    assert name == "Vanguard Australian Shares ETF"
    assert price == 95.50
    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()


@patch(
    "callbacks.transaction_callbacks.get_etf_name", return_value="Vanguard Australian Shares ETF"
)
@patch("callbacks.transaction_callbacks.get_connection")
@patch("callbacks.transaction_callbacks.get_ticker_cached")
def test_discover_ticker_success_yf(
    mock_get_ticker: MagicMock,
    mock_conn_func: MagicMock,
    mock_get_etf_name: MagicMock,
    mock_app: MockDashApp,
) -> None:
    discover_func = mock_app.callbacks.get("discover_ticker")
    assert discover_func is not None

    # Ticker not in DB, fallback to yfinance
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_conn_func.return_value = mock_conn

    mock_ticker_obj = MagicMock()
    mock_ticker_obj.fast_info.last_price = 96.25
    mock_get_ticker.return_value = mock_ticker_obj

    name, price = discover_func("VAS")
    assert name == "Vanguard Australian Shares ETF"
    assert price == 96.25
    mock_get_ticker.assert_called_once_with("VAS.AX")


@patch("callbacks.transaction_callbacks.get_etf_name", side_effect=Exception("Database error"))
def test_discover_ticker_exception(mock_get_etf_name: MagicMock, mock_app: MockDashApp) -> None:
    discover_func = mock_app.callbacks.get("discover_ticker")
    assert discover_func is not None

    name, price = discover_func("VAS")
    assert name == ""
    assert price == dash.no_update


def test_add_transaction_no_click(mock_app: MockDashApp) -> None:
    add_func = mock_app.callbacks.get("add_transaction")
    assert add_func is not None

    assert add_func(None, "buy", "VAS", 10, 95.0, "2026-01-01") == ("", {}, dash.no_update)
    assert add_func(0, "buy", "VAS", 10, 95.0, "2026-01-01") == ("", {}, dash.no_update)


def test_add_transaction_missing_fields(mock_app: MockDashApp) -> None:
    add_func = mock_app.callbacks.get("add_transaction")
    assert add_func is not None

    res_msg, res_style, res_store = add_func(1, None, "VAS", 10, 95.0, "2026-01-01")
    assert "Please fill all fields" in res_msg
    assert res_style["color"] == "var(--red)"
    assert res_store == dash.no_update


@patch(
    "callbacks.transaction_callbacks.validate_transaction",
    return_value=(False, "Invalid shares count"),
)
def test_add_transaction_invalid(mock_val: MagicMock, mock_app: MockDashApp) -> None:
    add_func = mock_app.callbacks.get("add_transaction")
    assert add_func is not None

    res_msg, res_style, res_store = add_func(1, "buy", "VAS", -5, 95.0, "2026-01-01")
    assert "Invalid shares count" in res_msg
    assert res_style["color"] == "var(--red)"
    assert res_store == dash.no_update


@patch("callbacks.transaction_callbacks.validate_transaction", return_value=(True, ""))
def test_add_transaction_success(mock_val: MagicMock, mock_app: MockDashApp) -> None:
    add_func = mock_app.callbacks.get("add_transaction")
    assert add_func is not None

    res_msg, res_style, res_store = add_func(1, "buy", "VAS", 10, 95.0, "2026-01-01")
    assert "Added BUY 10.00 VAS" in res_msg
    assert res_style["color"] == "var(--green)"
    assert res_store is True


@patch("callbacks.transaction_callbacks.txn_table", return_value="mock-table")
def test_update_transaction_log(mock_table: MagicMock, mock_app: MockDashApp) -> None:
    log_func = mock_app.callbacks.get("update_transaction_log")
    assert log_func is not None

    # Trigger with history
    assert log_func([{"type": "buy"}]) == "mock-table"
    # Trigger with empty history
    assert log_func(None) == "mock-table"


def test_clear_message(mock_app: MockDashApp) -> None:
    clear_func = mock_app.callbacks.get("clear_message")
    assert clear_func is not None

    # Should clear if message contains check or cross
    assert clear_func(1, "✅ Added") == ""
    assert clear_func(1, "❌ Error") == ""

    # Should not clear or update if not matching pattern
    assert clear_func(1, "Processing...") == dash.no_update
    assert clear_func(1, None) == dash.no_update


@patch("callbacks.transaction_callbacks.validate_transaction", return_value=(True, ""))
def test_add_transaction_normalization(mock_val: MagicMock, mock_app: MockDashApp) -> None:
    add_func = mock_app.callbacks.get("add_transaction")
    assert add_func is not None

    # Ticker with .ax or .AX should be normalized to VAS
    res_msg, res_style, res_store = add_func(1, "buy", "VAS.ax", 10, 95.0, "2026-01-01")
    assert "Added BUY 10.00 VAS" in res_msg
    assert res_store is True

    # Validate that validate_transaction was called with the normalized ticker
    mock_val.assert_called_with(
        {"type": "buy", "ticker": "VAS", "shares": 10.0, "price": 95.0, "date": "2026-01-01"}
    )
