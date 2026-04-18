"""
test/test_alert_service.py
==========================
Unit tests for alerts module.

Tests alert condition detection with configurable thresholds.
"""

import pytest
from services.alert_service import check_alerts


class TestCheckAlerts:
    """Test alert detection."""

    def test_no_alerts_when_portfolio_positive(self):
        """No alerts when portfolio is up."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": 10.0,
                "total_cost": 1000.0,
                "mkt_value": 1100.0,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 0

    def test_individual_drawdown_alert(self):
        """Alert triggered when individual holding down 20%+."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -25.0,
                "total_cost": 1000.0,
                "mkt_value": 750.0,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "drawdown"
        assert alerts[0]["ticker"] == "VHY"
        assert "-25.00%" in alerts[0]["message"]

    def test_portfolio_drawdown_alert(self):
        """Alert triggered when portfolio down 15%+."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -10.0,
                "total_cost": 500.0,
                "mkt_value": 450.0,
            },
            {
                "ticker": "VAS",
                "pnl_pct": -20.0,
                "total_cost": 500.0,
                "mkt_value": 400.0,
            },
        ]
        alerts = check_alerts(holdings)
        portfolio_alerts = [a for a in alerts if a["type"] == "portfolio"]
        assert len(portfolio_alerts) == 1
        # Total: cost=1000, value=850, down 15%
        assert "-15.00%" in portfolio_alerts[0]["message"]

    def test_custom_thresholds(self):
        """Custom thresholds should override defaults."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -18.0,  # Below default 20% but above custom 15%
                "total_cost": 1000.0,
                "mkt_value": 820.0,
            }
        ]
        # With default thresholds (-20%), no alert
        alerts_default = check_alerts(holdings)
        assert len(alerts_default) == 0

        # With custom threshold (-15%), should alert
        custom_thresholds = {"individual_drawdown": -15.0, "portfolio_drawdown": -10.0}
        alerts_custom = check_alerts(holdings, thresholds=custom_thresholds)
        assert len(alerts_custom) == 1
        assert alerts_custom[0]["type"] == "drawdown"

    def test_multiple_individual_alerts(self):
        """Multiple holdings can trigger individual alerts."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -25.0,
                "total_cost": 500.0,
                "mkt_value": 375.0,
            },
            {
                "ticker": "VAS",
                "pnl_pct": -22.0,
                "total_cost": 500.0,
                "mkt_value": 390.0,
            },
        ]
        alerts = check_alerts(holdings)
        drawdown_alerts = [a for a in alerts if a["type"] == "drawdown"]
        assert len(drawdown_alerts) == 2

    def test_exactly_at_threshold(self):
        """Position exactly at threshold should trigger alert (<=)."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -20.0,  # Exactly at default threshold
                "total_cost": 1000.0,
                "mkt_value": 800.0,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 1

    def test_just_above_threshold(self):
        """Position just above threshold should not alert."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": -19.9,
                "total_cost": 1000.0,
                "mkt_value": 800.1,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 0

    def test_zero_cost_basis_skipped(self):
        """Holdings with zero cost basis should not trigger alerts."""
        holdings = [
            {
                "ticker": "VHY",
                "pnl_pct": 0,
                "total_cost": 0.0,  # Zero cost
                "mkt_value": 100.0,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 0

    def test_empty_holdings_no_alerts(self):
        """Empty holdings list should produce no alerts."""
        alerts = check_alerts([])
        assert len(alerts) == 0

    def test_missing_pnl_pct_defaults_to_zero(self):
        """Missing pnl_pct should default to 0 (no alert)."""
        holdings = [
            {
                "ticker": "VHY",
                # Missing: pnl_pct
                "total_cost": 1000.0,
                "mkt_value": 900.0,
            }
        ]
        alerts = check_alerts(holdings)
        assert len(alerts) == 0
