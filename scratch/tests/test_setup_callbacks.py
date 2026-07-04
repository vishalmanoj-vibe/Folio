# scratch/tests/test_setup_callbacks.py
import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.setup_callbacks import register_setup_callbacks


class MockDashApp:
    """Mock Dash harness to capture registered callbacks."""

    def __init__(self) -> None:
        self.callbacks = {}
        self.clientside_callbacks = {}

    def callback(self, *args, **kwargs):
        def decorator(func):
            self.callbacks[func.__name__] = func
            return func

        return decorator

    def clientside_callback(self, code, *args, **kwargs):
        self.clientside_callbacks[code] = args


@pytest.fixture
def mock_app() -> MockDashApp:
    app = MockDashApp()
    register_setup_callbacks(app)
    return app


# ── Test auto_start_fetch ──────────────────────────────────────────────────


@patch("data.database.enqueue_task")
@patch("callbacks.setup_callbacks.repo")
def test_auto_start_fetch(mock_repo, mock_enqueue, mock_app):
    auto_start_func = mock_app.callbacks.get("auto_start_fetch")
    assert auto_start_func is not None

    # Case 1: Wrong pathname
    res = auto_start_func(1, "/portfolio", None)
    assert res == (dash.no_update, dash.no_update)

    # Case 2: Store already has tasks
    res = auto_start_func(1, "/setup/ready", {"tasks": ["task1"]})
    assert res == (dash.no_update, False)

    # Case 3: Fresh start enqueuing tasks
    mock_repo.load_transactions.return_value = [{"type": "buy", "ticker": "VAS", "shares": 10}]
    mock_enqueue.side_effect = [
        "task-refresh",
        "task-history-VAS",
        "task-benchmarks",
        "task-maintenance",
        "task-scrape-VAS",
    ]

    store_data, poll_disabled = auto_start_func(1, "/setup/ready", None)
    assert poll_disabled is False
    assert store_data is not None
    assert store_data["critical_task_id"] == "task-refresh"
    assert (
        len(store_data["tasks"]) == 5
    )  # refresh, history, benchmarks, maintenance, scrape_holdings

    task_types = [t["type"] for t in store_data["tasks"]]
    assert "refresh_portfolio" in task_types
    assert "fetch_history" in task_types
    assert "fetch_benchmarks" in task_types
    assert "maintenance" in task_types
    assert "scrape_holdings" in task_types


# ── Test poll_init_progress ──────────────────────────────────────────────────


@patch("callbacks.setup_callbacks._get_task_statuses")
def test_poll_init_progress(mock_statuses, mock_app):
    poll_func = mock_app.callbacks.get("poll_init_progress")
    assert poll_func is not None

    # Case 1: Wrong pathname
    res = poll_func(1, {}, "/portfolio")
    assert all(x == dash.no_update for x in res)

    # Case 2: No store data
    res = poll_func(1, None, "/setup/ready")
    assert all(x == dash.no_update for x in res)

    # Case 3: Still fetching (not all done, critical done)
    mock_statuses.return_value = {
        "task-refresh": {"status": "complete"},
        "task-history": {"status": "running"},
        "task-benchmarks": {"status": "pending"},
    }
    store_data = {
        "tasks": [
            {"id": "task-refresh", "label": "Prices", "is_critical": True},
            {"id": "task-history", "label": "History", "is_critical": False},
            {"id": "task-benchmarks", "label": "Benchmarks", "is_critical": False},
        ],
        "critical_task_id": "task-refresh",
        "phase": "fetching",
        "started_at": datetime.now().isoformat(),  # Prevent timeout in tests
    }

    res = poll_func(1, store_data, "/setup/ready")
    # Return signature has 12 elements
    assert len(res) == 12
    # Output 5 is launch_disabled (button disabled status)
    # Since all_done is False and timed_out is False, launch_disabled should be True
    assert res[4] is True

    # Case 4: All done
    mock_statuses.return_value = {
        "task-refresh": {"status": "complete"},
        "task-history": {"status": "complete"},
        "task-benchmarks": {"status": "complete"},
    }
    res = poll_func(2, store_data, "/setup/ready")
    # Since all_done is True, launch_disabled should be False (i.e. button is enabled)
    assert res[4] is False
    # Output 6 is poll-interval disabled status (should be True to stop polling)
    assert res[5] is True
    # Output 7 is the new store state (phase should be ready)
    assert res[6]["phase"] == "ready"


# ── Test handle_ready_launch ─────────────────────────────────────────────────


@patch("callbacks.setup_callbacks.repo")
def test_handle_ready_launch(mock_repo, mock_app):
    launch_func = mock_app.callbacks.get("handle_ready_launch")
    assert launch_func is not None

    # Case 1: Triggered by back button
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ready-back-btn.n_clicks", "value": 1}]
        mock_ctx.triggered_id = "setup-ready-back-btn"

        pathname, is_first_run, feedback = launch_func(None, 1)
        assert is_first_run == dash.no_update
        assert feedback.pathname == "/setup/ai"

    # Case 2: Triggered by launch button
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ready-launch-btn.n_clicks", "value": 1}]
        mock_ctx.triggered_id = "setup-ready-launch-btn"

        pathname, is_first_run, feedback = launch_func(1, None)
        assert is_first_run is False
        assert feedback.pathname == "/"
        mock_repo.set_onboarding_completed.assert_called_once_with(True)


# ── Test Strategy & AI settings ─────────────────────────────────────────────


@patch("data.settings_repository.get_all_settings")
def test_load_setup_settings(mock_get_all, mock_app):
    load_settings_func = mock_app.callbacks.get("load_setup_settings")
    assert load_settings_func is not None

    # Case 1: Wrong pathname
    res = load_settings_func("/portfolio")
    assert res == (dash.no_update, dash.no_update, dash.no_update, dash.no_update)

    # Case 2: Empty settings (falls back to defaults)
    mock_get_all.return_value = {}
    res = load_settings_func("/setup/ai")
    assert res == ("Balanced", "Moderate", "37%", "gemini")

    # Case 3: Load existing settings
    mock_get_all.return_value = {
        "investment_goal": "Growth",
        "risk_tolerance": "High",
        "tax_bracket": "45%",
        "ai_provider": "openai",
    }
    res = load_settings_func("/setup/ai")
    assert res == ("Growth", "High", "45%", "openai")


@patch("data.settings_repository.save_setting")
@patch("callbacks.setup_callbacks.repo")
def test_handle_ai_setup(mock_repo, mock_save, mock_app):
    handle_setup_func = mock_app.callbacks.get("handle_ai_setup")
    assert handle_setup_func is not None

    # Case 1: Back button
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ai-back-btn.n_clicks", "value": 1}]
        pathname, feedback = handle_setup_func(
            None,
            None,
            1,
            "gemini",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "",
            "Balanced",
            "Moderate",
            "37%",
        )
        assert pathname == dash.no_update
        assert feedback.pathname == "/setup/portfolio"

    # Case 2: Skip button (clears API Key, defaults strategy settings to Balanced)
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ai-skip-btn.n_clicks", "value": 1}]
        pathname, feedback = handle_setup_func(
            None,
            1,
            None,
            "gemini",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "",
            "Growth",
            "High",
            "45%",
        )

        # Verify defaults are saved
        mock_save.assert_any_call("investment_goal", "Balanced")
        mock_save.assert_any_call("risk_tolerance", "Moderate")
        mock_save.assert_any_call("tax_bracket", "37%")
        mock_repo.set_api_key.assert_any_call("gemini", "")
        mock_repo.set_api_key.assert_any_call("openai", "")
        mock_repo.set_api_key.assert_any_call("anthropic", "")

        assert pathname == dash.no_update
        assert feedback.pathname == "/setup/ready"

    # Case 3: Save button with selected strategy and empty API Key
    mock_save.reset_mock()
    mock_repo.reset_mock()
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ai-save-btn.n_clicks", "value": 1}]
        pathname, feedback = handle_setup_func(
            1,
            None,
            None,
            "gemini",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "",
            "Growth",
            "High",
            "45%",
        )

        mock_save.assert_any_call("investment_goal", "Growth")
        mock_save.assert_any_call("risk_tolerance", "High")
        mock_save.assert_any_call("tax_bracket", "45%")
        mock_repo.set_api_key.assert_called_with("gemini", "")

        assert pathname == dash.no_update
        assert feedback.pathname == "/setup/ready"

    # Case 4: Save button with selected strategy and API Key
    mock_save.reset_mock()
    mock_repo.reset_mock()
    with patch("dash.callback_context") as mock_ctx:
        mock_ctx.triggered = [{"prop_id": "setup-ai-save-btn.n_clicks", "value": 1}]
        pathname, feedback = handle_setup_func(
            1,
            None,
            None,
            "gemini",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "MY-GEMINI-KEY",
            "Income",
            "Low",
            "15%",
        )

        mock_save.assert_any_call("investment_goal", "Income")
        mock_save.assert_any_call("risk_tolerance", "Low")
        mock_save.assert_any_call("tax_bracket", "15%")
        mock_repo.set_api_key.assert_called_with("gemini", "MY-GEMINI-KEY")

        assert pathname == dash.no_update
        assert feedback.pathname == "/setup/ready"


@patch("data.settings_repository.get_all_settings")
@patch("callbacks.setup_callbacks.repo")
def test_update_setup_provider_models_and_key(mock_repo, mock_get_all, mock_app):
    update_func = mock_app.callbacks.get("update_setup_provider_models_and_key")
    assert update_func is not None

    # Case 1: Wrong pathname
    res = update_func("gemini", "/portfolio")
    assert res == (
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )

    # Case 2: Gemini selected, empty key
    mock_get_all.return_value = {}
    mock_repo.get_api_key.return_value = None
    with patch.dict(os.environ, {}, clear=True):
        res = update_func("gemini", "/setup/ai")
    assert len(res) == 6
    assert "gemini-2.5-flash" in [opt["value"] for opt in res[0]]
    assert res[1] == "gemini-2.5-flash"
    assert res[4] == "Enter Gemini API Key (e.g. AIzaSy...)"
    assert res[5] == ""

    # Case 3: OpenAI selected, existing key in DB
    mock_get_all.return_value = {"ai_provider": "openai", "ai_chat_model": "gpt-4o"}
    mock_repo.get_api_key.return_value = "my-openai-key"
    with patch.dict(os.environ, {}, clear=True):
        res = update_func("openai", "/setup/ai")
    assert len(res) == 6
    assert "gpt-4o" in [opt["value"] for opt in res[0]]
    assert res[1] == "gpt-4o"
    assert res[4] == "Enter OpenAI API Key (e.g. sk-proj-...)"
    assert res[5] == "••••••••••••••••"


@patch("services.ai_provider.generate_content")
@patch("callbacks.setup_callbacks.repo")
def test_test_setup_ai_connection(mock_repo, mock_generate, mock_app):
    test_func = mock_app.callbacks.get("test_setup_ai_connection")
    assert test_func is not None

    # Case 1: Empty key
    res = test_func(1, "gemini", "")
    assert "API key is empty" in res[0]
    assert res[1]["color"] == "var(--red)"

    # Case 2: Successful Gemini test connection
    mock_generate.return_value = "OK"
    res = test_func(1, "gemini", "my-valid-key")
    assert "Connection successful" in res[0]
    assert res[1]["color"] == "var(--green)"

    # Case 3: Connection failure response
    mock_generate.return_value = "Error: Invalid API Key"
    res = test_func(1, "gemini", "my-invalid-key")
    assert "Connection failed" in res[0]
    assert res[1]["color"] == "var(--red)"
