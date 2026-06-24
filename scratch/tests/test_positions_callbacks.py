# scratch/tests/test_positions_callbacks.py
"""Unit tests for the Positions page callbacks, specifically select_ticker."""

from typing import Any
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.positions_callbacks import register_callbacks


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
    """Mock holdings payload matching portfolio-store structure."""
    return {
        "fetched_at": "12:00:00",
        "holdings": [
            {"ticker": "AINF", "total_shares": 10.0},
            {"ticker": "VAS", "total_shares": 20.0},
            {"ticker": "CBA", "total_shares": 30.0},
        ],
    }


def test_select_ticker_off_page(mock_app: MockDashApp) -> None:
    """Verify that select_ticker returns dash.no_update when off-page."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx"):
        # User is on home page
        res = func([0, 0], "", "/", {}, None)
        assert res == dash.no_update


def test_select_ticker_card_click(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify that clicking a card selects that ticker."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        # Mock triggering by clicking the VAS card
        mock_ctx.triggered_id = {"type": "pos-card", "index": "VAS"}
        mock_ctx.triggered = [{"prop_id": '{"index":"VAS","type":"pos-card"}.n_clicks', "value": 1}]

        res = func([0, 1, 0], "", "/positions", mock_portfolio_data, "AINF")
        assert res == "VAS"


def test_select_ticker_card_ghost_click(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify that ghost clicks (n_clicks=0) are ignored."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "pos-card", "index": "VAS"}
        # value is 0 (initial insertion)
        mock_ctx.triggered = [{"prop_id": '{"index":"VAS","type":"pos-card"}.n_clicks', "value": 0}]

        res = func([0, 0, 0], "", "/positions", mock_portfolio_data, "AINF")
        assert res == dash.no_update


def test_select_ticker_url_deep_link(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify that url.search parameters select the correct ticker on page load."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "url"
        mock_ctx.triggered = [{"prop_id": "url.search", "value": "?ticker=VAS"}]

        # Triggered by url search param change, current is "AINF"
        res = func([0, 0, 0], "?ticker=VAS", "/positions", mock_portfolio_data, "AINF")
        assert res == "VAS"


def test_select_ticker_url_deep_link_invalid_ticker(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify that invalid tickers in url.search fall back gracefully."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "url"
        mock_ctx.triggered = [{"prop_id": "url.search", "value": "?ticker=INVALID"}]

        # Triggered by url, ticker is invalid, should fall back to current (AINF)
        res = func([0, 0, 0], "?ticker=INVALID", "/positions", mock_portfolio_data, "AINF")
        assert res == "AINF"


def test_select_ticker_background_refresh_preserves_current(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify that background data refreshes do not overwrite manual card selections."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        # Triggered by portfolio-store refresh, not URL
        mock_ctx.triggered_id = "portfolio-store"
        mock_ctx.triggered = [{"prop_id": "portfolio-store.data", "value": mock_portfolio_data}]

        # Current manual selection is "VAS" (different from URL search param if it remains unchanged)
        res = func([0, 0, 0], "?ticker=AINF", "/positions", mock_portfolio_data, "VAS")
        assert res == "VAS"


def test_select_ticker_default_fallback(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Verify default selection logic falls back to first ticker when current is None."""
    func = mock_app.callbacks.get("select_ticker")
    assert func is not None

    with patch("callbacks.positions_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = None
        mock_ctx.triggered = []

        # No url search, current is None
        res = func([0, 0, 0], "", "/positions", mock_portfolio_data, None)
        assert res == "AINF"
