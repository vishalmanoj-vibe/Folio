from typing import Any
from unittest.mock import MagicMock, patch

import dash
import pytest

from callbacks.settings_callbacks import make_weight_bar, register_callbacks


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


def test_make_weight_bar() -> None:
    div = make_weight_bar("Test Weight", 0.35)
    assert div is not None
    assert "35%" in div.children[0].children[1].children


def test_load_user_settings_not_settings(mock_app: MockDashApp) -> None:
    load_func = mock_app.callbacks.get("load_user_settings")
    assert load_func is not None

    res = load_func("/portfolio")
    assert res == (dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update)


def test_load_user_settings_success(mock_app: MockDashApp) -> None:
    load_func = mock_app.callbacks.get("load_user_settings")
    assert load_func is not None

    mock_settings = {
        "investment_goal": "Growth",
        "risk_tolerance": "High",
        "tax_bracket": "45%",
        "ai_chat_model": "gemini-2.5-pro",
        "ai_report_model": "gemini-2.5-pro",
    }

    with patch(
        "callbacks.settings_callbacks.get_all_settings", return_value=mock_settings
    ) as mock_get:
        res = load_func("/settings")
        assert res == ("Growth", "High", "45%", "gemini-2.5-pro", "gemini-2.5-pro")
        mock_get.assert_called_once()


def test_update_weight_preview(mock_app: MockDashApp) -> None:
    update_func = mock_app.callbacks.get("update_weight_preview")
    assert update_func is not None

    # Off page
    assert update_func("/portfolio", "Balanced", "Moderate") == dash.no_update

    # Missing goal or risk
    assert update_func("/settings", None, "Moderate") == dash.no_update

    # Success
    mock_weights = {"trend": 0.30, "momentum": 0.20, "value": 0.15, "cost": 0.15, "risk": 0.20}
    with patch(
        "callbacks.settings_callbacks.get_profile_weights", return_value=mock_weights
    ) as mock_get_weights:
        res = update_func("/settings", "Balanced", "Moderate")
        assert len(res) == 5
        mock_get_weights.assert_called_once_with("Balanced", "Moderate")


def test_save_user_settings(mock_app: MockDashApp) -> None:
    save_func = mock_app.callbacks.get("save_user_settings")
    assert save_func is not None

    # Off page or no clicks
    assert (
        save_func(0, "/settings", "Balanced", "Moderate", "37%", "model1", "model2")
        == dash.no_update
    )
    assert (
        save_func(1, "/portfolio", "Balanced", "Moderate", "37%", "model1", "model2")
        == dash.no_update
    )

    # Success
    with patch("callbacks.settings_callbacks.save_setting") as mock_save:
        res = save_func(
            1,
            "/settings",
            "Balanced",
            "Moderate",
            "37%",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
        )
        assert "✓ Profile settings saved successfully" in res
        assert mock_save.call_count == 5
        mock_save.assert_any_call("investment_goal", "Balanced")
