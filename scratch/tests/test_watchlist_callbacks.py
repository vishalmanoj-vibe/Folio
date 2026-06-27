import json
from typing import Any
from unittest.mock import MagicMock, patch

import dash
import pandas as pd
import pytest

from callbacks.watchlist_callbacks import register_callbacks, repo


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


# ── 1. Store updates ──
@patch("services.market.market_status.is_market_open", return_value=False)
def test_update_watchlist_store_market_closed(mock_open: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_watchlist_store")
    assert func is not None

    with patch("callbacks.watchlist_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "price-interval"
        assert func(None, None, None, 1, None, None, None, None) == (dash.no_update, dash.no_update)


@patch("callbacks.watchlist_callbacks.fetch_live")
def test_update_watchlist_store_add_remove_order(
    mock_fetch: MagicMock, mock_app: MockDashApp
) -> None:
    func = mock_app.callbacks.get("update_watchlist_store")
    assert func is not None

    mock_fetch.return_value = ({"holdings": [{"ticker": "VAS"}]}, None, None)

    # Mock repo methods
    repo.add_ticker = MagicMock()
    repo.remove_ticker = MagicMock()
    repo.update_watchlist_order = MagicMock()
    repo.load_watchlist = MagicMock(return_value=[{"ticker": "VAS"}, {"ticker": "VGS"}])

    with patch("callbacks.watchlist_callbacks.ctx") as mock_ctx:
        # Add ticker
        mock_ctx.triggered_id = "watchlist-add-btn"
        res, clear = func(1, None, None, None, None, None, "VAS", None)
        repo.add_ticker.assert_called_once_with("VAS")
        assert res["holdings"][0]["ticker"] == "VAS"
        assert clear == ""

        # Remove ticker
        repo.load_watchlist.return_value = [{"ticker": "VGS"}]
        mock_ctx.triggered_id = {"type": "watchlist-remove-btn", "index": "VAS"}
        mock_ctx.triggered = [{"value": 1}]
        res, clear = func(None, [1], None, None, None, None, None, None)
        repo.remove_ticker.assert_called_once_with("VAS")

        # Reorder tickers
        repo.load_watchlist.return_value = [{"ticker": "VGS"}, {"ticker": "VAS"}]
        mock_ctx.triggered_id = "watchlist-order-input"
        res, clear = func(None, None, None, None, None, '["VGS", "VAS"]', None, None)
        repo.update_watchlist_order.assert_called_once_with(["VGS", "VAS"])


# ── 2. Table Render ──
@patch("data.database.get_connection")
def test_render_watchlist_table(mock_conn_func: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("render_watchlist_table")
    assert func is not None

    # Off page
    assert func({}, "/portfolio", None, {}) == (dash.no_update, dash.no_update)

    # Empty store
    res_empty, msg = func(None, "/watchlist", None, {})
    assert "watchlist is empty" in res_empty.children

    # Mock sentiment db
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [
        {"ticker": "VAS", "sentiment": "Positive", "score": 0.5}
    ]
    mock_conn_func.return_value = mock_conn

    # Normal watchlist data
    mock_data = {
        "holdings": [
            {
                "ticker": "VAS",
                "name": "Vanguard ASX",
                "last_price": 95.0,
                "day_chg": 0.5,
                "day_chg_pct": 0.53,
                "day_high": 96.0,
                "day_low": 94.0,
                "div_yield": 4.2,
            }
        ]
    }
    table, msg = func(mock_data, "/watchlist", "VAS", {})
    assert table is not None
    assert msg == ""
    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()


# ── 3. Ticker Selection ──
def test_select_watchlist_ticker(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("select_watchlist_ticker")
    assert func is not None

    with patch("callbacks.watchlist_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "watchlist-select-ticker", "index": "VAS"}
        mock_ctx.triggered = [{"value": 1}]
        assert func([1], None, "VGS") == "VAS"

        # No click trigger value
        mock_ctx.triggered = [{"value": 0}]
        assert func([0], None, "VGS") == "VGS"


def test_seed_default_ticker(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("seed_default_ticker")
    assert func is not None

    # Already has selection
    assert func({}, "VGS") == dash.no_update

    # No selection, seeds default
    assert func({"holdings": [{"ticker": "VAS"}]}, None) == "VAS"


# ── 4. Watchlist Chart ──
@patch("data.repository.HistoryRepository")
def test_update_watchlist_chart(mock_repo_cls: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_watchlist_chart")
    assert func is not None

    # Off page
    fig, title = func("VAS", {}, "/portfolio", "dark", "1y")
    assert title == "Price Performance"

    # No selection
    fig, title = func(None, {}, "/watchlist", "dark", "1y")
    assert title == "Price Performance"

    # Mock historical data
    mock_repo = MagicMock()
    mock_series = pd.Series(
        [100, 101, 102], index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])
    )
    mock_repo.load_close_series.return_value = mock_series
    mock_repo_cls.return_value = mock_repo

    fig, title = func("VAS", {}, "/watchlist", "dark", "1y")
    assert "Price Performance: VAS" in title
    assert len(fig.data) == 1
    assert fig.data[0].name == "VAS"


# ── 5. Sync Period ──
def test_sync_watchlist_period(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("sync_watchlist_period")
    assert func is not None

    # No trigger
    with patch("callbacks.watchlist_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = None
        assert func([]) == dash.no_update

        # Valid trigger
        mock_ctx.triggered_id = {"type": "wl-period-btn", "index": "6mo"}
        assert func([1]) == "6mo"


def test_update_period_btn_styles(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("update_period_btn_styles")
    assert func is not None

    styles = func("6mo")
    assert styles == ["btn-sm", "btn-sm btn-primary", "btn-sm", "btn-sm", "btn-sm"]


# ── 6. Stat Cards & AI Insights ──
@patch("data.repository.HistoryRepository")
def test_render_watchlist_stat_cards(mock_repo_cls: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("render_watchlist_stat_cards")
    assert func is not None

    # Empty data
    assert func("VAS", None, None) == ([], None, None)

    # Valid data, no AI signals
    mock_data = {
        "holdings": [
            {
                "ticker": "VAS",
                "last_price": 95.0,
                "day_chg": 0.5,
                "day_chg_pct": 0.53,
                "day_high": 96.0,
                "day_low": 94.0,
                "div_yield": 4.2,
                "annual_div": 4.0,
                "div_frequency": "Quarterly",
            }
        ]
    }
    mock_repo = MagicMock()
    mock_repo.load_close_series.return_value = pd.Series([90, 95])
    mock_repo_cls.return_value = mock_repo

    cards, tech, ai = func("VAS", mock_data, None)
    assert len(cards) == 4
    assert tech is not None
    assert ai is None

    # With AI signals
    mock_signals = {
        "ai": {
            "VAS": {"verdict": "Confident", "explanation": "Looks good", "risks": ["Drawdown risk"]}
        },
        "raw": {"VAS": {"score": 0.8, "reasons": ["Bullish trend"]}},
    }
    cards, tech, ai = func("VAS", mock_data, mock_signals)
    assert ai is not None
    # Verify risk text is present
    assert "Confident" in str(ai.children)


@patch("data.repository.HistoryRepository")
def test_render_watchlist_stat_cards_empty_history(
    mock_repo_cls: MagicMock, mock_app: MockDashApp
) -> None:
    func = mock_app.callbacks.get("render_watchlist_stat_cards")
    assert func is not None

    mock_data = {
        "holdings": [
            {
                "ticker": "VAS",
                "last_price": 95.0,
                "day_chg": 0.5,
                "day_chg_pct": 0.53,
                "day_high": 96.0,
                "day_low": 94.0,
                "div_yield": 4.2,
                "annual_div": 4.0,
                "div_frequency": "Quarterly",
            }
        ]
    }
    mock_repo = MagicMock()
    mock_repo.load_close_series.return_value = pd.Series(dtype=float)
    mock_repo_cls.return_value = mock_repo

    cards, tech, ai = func("VAS", mock_data, None)
    assert len(cards) == 4
    assert tech is None
    assert ai is None


# ── 7. Notes ──
def test_load_note_for_ticker(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("load_note_for_ticker")
    assert func is not None

    assert func(None) == ""

    repo.load_notes = MagicMock(return_value={"VAS": "My note content"})
    assert func("VAS") == "My note content"


def test_save_note_for_ticker(mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("save_note_for_ticker")
    assert func is not None

    assert func(1, None, "Text") == "No ticker selected"

    repo.save_note = MagicMock()
    assert func(1, "VAS", "My new note") == "✓ Saved"
    repo.save_note.assert_called_once_with("VAS", "My new note")


# ── 8. Discovery ──
@patch("callbacks.watchlist_callbacks.get_etf_name", return_value="Vanguard ETF")
def test_discover_watchlist_ticker(mock_get_name: MagicMock, mock_app: MockDashApp) -> None:
    func = mock_app.callbacks.get("discover_watchlist_ticker")
    assert func is not None

    assert func("") == ""
    assert func("VAS") == "Vanguard ETF"
    mock_get_name.assert_called_once_with("VAS")
