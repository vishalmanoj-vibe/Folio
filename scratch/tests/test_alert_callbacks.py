from typing import Any

import pytest
from dash import html

from callbacks.alert_callbacks import register_callbacks
from services.alert_service import check_alerts


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


def test_check_alerts() -> None:
    # 1. Test empty holdings
    assert check_alerts([]) == []

    # 2. Test holding with no drawdown and no portfolio drawdown
    holdings = [{"ticker": "VAS", "total_cost": 100.0, "mkt_value": 110.0, "pnl_pct": 10.0}]
    assert check_alerts(holdings) == []

    # 3. Test holding with individual drawdown (-25% <= -20.0%) but portfolio drawdown is not triggered
    holdings_individual_dd = [
        {"ticker": "VAS", "total_cost": 100.0, "mkt_value": 75.0, "pnl_pct": -25.0},
        {"ticker": "VGS", "total_cost": 200.0, "mkt_value": 200.0, "pnl_pct": 0.0},
    ]
    alerts = check_alerts(holdings_individual_dd)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "drawdown"
    assert alerts[0]["ticker"] == "VAS"
    assert "VAS down -25.00%" in alerts[0]["message"]

    # 4. Test portfolio drawdown (-18% <= -15.0%) but individual drawdown is not triggered
    # individual is -18% (not yet -20%) but portfolio is -18%
    holdings_portfolio_dd = [
        {"ticker": "VAS", "total_cost": 100.0, "mkt_value": 82.0, "pnl_pct": -18.0}
    ]
    alerts = check_alerts(holdings_portfolio_dd)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "portfolio"
    assert "Portfolio down -18.00%" in alerts[0]["message"]

    # 5. Test both individual and portfolio drawdown
    holdings_both_dd = [{"ticker": "VAS", "total_cost": 100.0, "mkt_value": 70.0, "pnl_pct": -30.0}]
    alerts = check_alerts(holdings_both_dd)
    assert len(alerts) == 2
    types = [a["type"] for a in alerts]
    assert "drawdown" in types
    assert "portfolio" in types


def test_show_alerts_callback(mock_app: MockDashApp) -> None:
    show_alerts_func = mock_app.callbacks.get("show_alerts")
    assert show_alerts_func is not None

    # Test None data
    banner, count, style = show_alerts_func(None)
    assert banner == ""
    assert count == ""
    assert style["display"] == "none"

    # Test missing holdings key
    banner, count, style = show_alerts_func({})
    assert banner == ""
    assert count == ""
    assert style["display"] == "none"

    # Test empty holdings (no alerts)
    banner, count, style = show_alerts_func({"holdings": []})
    assert banner == ""
    assert count == ""
    assert style["display"] == "none"

    # Test holdings with alerts
    data = {
        "holdings": [{"ticker": "VAS", "total_cost": 100.0, "mkt_value": 70.0, "pnl_pct": -30.0}]
    }
    banner, count, style = show_alerts_func(data)
    assert count == "2"
    assert style["display"] == "inline-block"
    assert isinstance(banner, html.Div)
    assert banner.className == "alerts-banner"
    assert len(banner.children) == 2
