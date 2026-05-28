from typing import Any

import dash
import pytest

from callbacks.portfolio_callbacks import register_callbacks


class MockDashApp:
    """Mock Dash application harness to capture and test nested callbacks."""

    def __init__(self) -> None:
        self.callbacks: dict[str, Any] = {}

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            # Capture the function reference by name
            self.callbacks[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_app() -> MockDashApp:
    """Fixture to initialize register_callbacks and capture functions."""
    app = MockDashApp()
    register_callbacks(app)  # Runs registration inside callbacks layer
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


def test_update_stats_prioritized_rendering(
    mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]
) -> None:
    """Assert that a url path mismatch immediately returns dash.no_update to prevent off-page redraws."""
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None

    # Trigger with an off-page URL (navigated to Watchlist)
    result = update_stats_func(mock_portfolio_data, "/watchlist")

    # Assert prioritized rendering blocks recalculation
    assert result == dash.no_update


def test_update_stats_skeletons_on_missing_data(mock_app: MockDashApp) -> None:
    """Assert that callbacks return layout skeletons safely instead of raising crashes on empty data."""
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None

    # Trigger with empty/missing holdings payload
    empty_data: dict[str, Any] = {"holdings": [], "fetched_at": ""}
    result: list[Any] = update_stats_func(empty_data, "/")

    assert isinstance(result, list)
    assert len(result) == 8  # Renders 8 skeletal cards
    assert getattr(result[0], "children", None) is not None


def test_update_stats_success(mock_app: MockDashApp, mock_portfolio_data: dict[str, Any]) -> None:
    """Assert callback correctly aggregates stats and returns styled stat cards."""
    update_stats_func = mock_app.callbacks.get("update_stats")
    assert update_stats_func is not None

    # Trigger on the home Portfolio page "/"
    result: list[Any] = update_stats_func(mock_portfolio_data, "/")

    assert isinstance(result, list)
    assert len(result) == 8  # 8 stat cards

    # Assert values calculated inside card indices
    total_val_card = result[0]
    cost_basis_card = result[1]

    assert "$950.00" in total_val_card.children[1].children
    assert "$900.00" in cost_basis_card.children[1].children
