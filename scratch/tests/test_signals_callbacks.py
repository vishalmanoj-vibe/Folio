# scratch/tests/test_signals_callbacks.py
import json
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.signals_callbacks import register_callbacks


class MockDashApp:
    """Mock Dash harness to capture registered callbacks."""

    def __init__(self) -> None:
        self.callbacks = {}

    def callback(self, *args, **kwargs):
        def decorator(func):
            self.callbacks[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_app() -> MockDashApp:
    app = MockDashApp()
    register_callbacks(app)
    return app


# ── Test Triggering Global Intelligence ──────────────────────────────────────


@patch("callbacks.signals_callbacks.enqueue_task")
@patch("data.repository.PortfolioRepository")
@patch("data.watchlist_repository.WatchlistRepository")
@patch("core.engine.build_holdings")
def test_trigger_global_intelligence(
    mock_build_holdings,
    mock_watchlist_repo,
    mock_portfolio_repo,
    mock_enqueue,
    mock_app,
):
    trigger_func = mock_app.callbacks.get("trigger_global_intelligence")
    assert trigger_func is not None

    # Case 1: n_clicks is None
    pending, label = trigger_func(None, None, None, None, None, None)
    assert pending == dash.no_update
    assert label == dash.no_update

    # Case 2: Standard trigger
    mock_portfolio_repo.return_value.load_transactions.return_value = [
        {"type": "buy", "ticker": "VAS", "shares": 10}
    ]
    mock_build_holdings.return_value = [{"ticker": "VAS"}]
    mock_watchlist_repo.return_value.load_watchlist.return_value = [{"ticker": "VGS"}]
    mock_enqueue.side_effect = ["uuid-task-portfolio", "uuid-task-watchlist"]

    pending, label = trigger_func(
        1,  # n_clicks
        None,  # port_data
        None,  # watch_data
        None,  # port_signals
        None,  # watch_signals
        [],  # pending
    )

    assert len(pending) == 2
    assert pending[0]["id"] == "uuid-task-portfolio"
    assert pending[0]["type"] == "signals"
    assert pending[1]["id"] == "uuid-task-watchlist"
    assert pending[1]["type"] == "watchlist_signals"
    assert label == "Updating Intelligence..."


# ── Test Task Polling & Result Processing ────────────────────────────────────


@patch("callbacks.signals_callbacks.get_connection")
@patch("callbacks.signals_callbacks._load_signal_results")
def test_poll_tasks_and_update_stores(mock_load_signals, mock_get_conn, mock_app):
    poll_func = mock_app.callbacks.get("poll_tasks_and_update_stores")
    assert poll_func is not None

    # Case 1: No pending tasks
    s_store, w_store, still_p, ref_trig = poll_func(0, [], None, None)
    assert s_store == dash.no_update
    assert still_p == []

    # Case 2: Completed tasks
    mock_conn = MagicMock()
    # Mock return values for queries: 1st task complete, 2nd task pending
    mock_conn.execute.return_value.fetchone.side_effect = [
        {"status": "complete"},
        {"status": "pending"},
    ]
    mock_get_conn.return_value = mock_conn
    mock_load_signals.return_value = {"raw": {"VAS": {"score": 0.8}}, "ai": {"VAS": {}}}

    pending_tasks = [
        {"id": "task-1", "type": "signals", "scope": "portfolio"},
        {"id": "task-2", "type": "watchlist_signals", "scope": "watchlist"},
    ]

    s_store, w_store, still_p, ref_trig = poll_func(
        1,  # n_intervals
        pending_tasks,
        None,
        None,
    )

    # task-1 was complete, so updates_needed["signals"] is True, and signals-store loaded
    assert s_store == {"raw": {"VAS": {"score": 0.8}}, "ai": {"VAS": {}}}
    # task-2 was pending, so still in pending
    assert len(still_p) == 1
    assert still_p[0]["id"] == "task-2"


# ── Test Global Status UI ───────────────────────────────────────────────────


def test_update_global_status(mock_app):
    status_func = mock_app.callbacks.get("update_global_status")
    assert status_func is not None

    # Case 1: Task is pending
    pending = [{"type": "signals"}]
    label, style = status_func(pending, None, None)
    assert label == "Updating Intelligence..."
    assert style["display"] == "flex"

    # Case 2: Generated at timestamp format check
    signals = {"generated_at": "2026-06-09T12:00:00"}
    label, style = status_func([], signals, None)
    assert "Updated 12:00" in label
