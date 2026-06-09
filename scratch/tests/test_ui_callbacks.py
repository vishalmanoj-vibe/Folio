from typing import Any
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.ui_callbacks import register_callbacks


class MockDashApp:
    def __init__(self) -> None:
        self.callbacks: dict[str, Any] = {}
        self.clientside_callbacks = []

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.callbacks[func.__name__] = func
            return func

        return decorator

    def clientside_callback(self, *args: Any, **kwargs: Any) -> Any:
        self.clientside_callbacks.append(args)
        return None


@pytest.fixture
def mock_app() -> MockDashApp:
    app = MockDashApp()
    register_callbacks(app)
    return app


def test_toggle_theme_store(mock_app: MockDashApp) -> None:
    toggle_func = mock_app.callbacks.get("toggle_theme_store")
    assert toggle_func is not None

    # Test toggling dark to light
    assert toggle_func(1, None, "dark") == "light"
    # Test toggling light to dark
    assert toggle_func(1, None, "light") == "dark"
    # Test fallback when current is None
    assert toggle_func(None, 1, None) == "dark"


def test_toggle_compact_mode(mock_app: MockDashApp) -> None:
    toggle_func = mock_app.callbacks.get("toggle_compact_mode")
    assert toggle_func is not None

    # Initial load (not n)
    state, opened, children, btn_class = toggle_func(None, None)
    assert state is True
    assert opened is False
    assert btn_class == "btn-primary btn-sm"

    # Toggle from compact (is_compact=True)
    state, opened, children, btn_class = toggle_func(1, True)
    assert state is False
    assert opened is True
    assert btn_class == "btn-sm"

    # Toggle from non-compact (is_compact=False)
    state, opened, children, btn_class = toggle_func(2, False)
    assert state is True
    assert opened is False
    assert btn_class == "btn-primary btn-sm"


def test_update_table_sorting_no_trigger(mock_app: MockDashApp) -> None:
    sort_func = mock_app.callbacks.get("update_table_sorting")
    assert sort_func is not None

    with patch("callbacks.ui_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = None
        assert sort_func([], None) == dash.no_update


def test_update_table_sorting_invalid_trigger(mock_app: MockDashApp) -> None:
    sort_func = mock_app.callbacks.get("update_table_sorting")
    assert sort_func is not None

    with patch("callbacks.ui_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "some-string-id"
        assert sort_func([], None) == dash.no_update

        mock_ctx.triggered_id = {"type": "not-table-th", "index": "ticker"}
        assert sort_func([], None) == dash.no_update

        mock_ctx.triggered_id = {"type": "table-th", "index": None}
        assert sort_func([], None) == dash.no_update


def test_update_table_sorting_success(mock_app: MockDashApp) -> None:
    sort_func = mock_app.callbacks.get("update_table_sorting")
    assert sort_func is not None

    with patch("callbacks.ui_callbacks.ctx") as mock_ctx:
        # Click new column, metric type (e.g. pnl_pct -> desc)
        mock_ctx.triggered_id = {"type": "table-th", "index": "pnl_pct"}
        new_state = sort_func([1], None)
        assert new_state["sort_col"] == "pnl_pct"
        assert new_state["sort_dir"] == "desc"

        # Click same column again, toggles to asc
        new_state_2 = sort_func([2], new_state)
        assert new_state_2["sort_col"] == "pnl_pct"
        assert new_state_2["sort_dir"] == "asc"

        # Click label column (ticker -> asc)
        mock_ctx.triggered_id = {"type": "table-th", "index": "ticker"}
        new_state_3 = sort_func([3], new_state_2)
        assert new_state_3["sort_col"] == "ticker"
        assert new_state_3["sort_dir"] == "asc"


def test_handle_refresh_click(mock_app: MockDashApp) -> None:
    refresh_func = mock_app.callbacks.get("handle_refresh_click")
    assert refresh_func is not None

    # No clicks
    assert refresh_func(None, None, []) == dash.no_update

    with patch("data.database.enqueue_task", return_value="task-123") as mock_enqueue:
        # Clicks
        res = refresh_func(1, None, None)
        assert res == [{"id": "task-123", "type": "refresh_portfolio"}]
        mock_enqueue.assert_called_once_with("refresh_portfolio", priority=1)
