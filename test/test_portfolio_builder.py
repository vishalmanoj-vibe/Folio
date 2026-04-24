# test/test_portfolio_builder.py
"""
test/test_portfolio_builder.py
==============================
Unit tests for portfolio_builder module.

Tests transaction validation, holdings aggregation, and edge cases.
"""

import pytest
from data.portfolio_builder import build_holdings, validate_transaction


class TestValidateTransaction:
    """Test transaction validation."""

    def test_valid_buy_transaction(self):
        """Valid buy transaction should pass."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            "shares": 10.0,
            "price": 81.50,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is True
        assert msg == ""

    def test_valid_sell_transaction(self):
        """Valid sell transaction should pass."""
        txn = {
            "type": "sell",
            "ticker": "VAS",
            "shares": 5.0,
            "price": 99.00,
            "date": "2026-02-01",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is True

    def test_missing_required_keys(self):
        """Transaction with missing keys should fail."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            # Missing: shares, price, date
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False
        assert "missing keys" in msg.lower()

    def test_invalid_shares_type(self):
        """Non-numeric shares should fail."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            "shares": "not_a_number",
            "price": 81.50,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False
        assert "numeric" in msg.lower()

    def test_negative_shares(self):
        """Negative shares should fail."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            "shares": -10.0,
            "price": 81.50,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False

    def test_zero_price(self):
        """Zero price should fail."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            "shares": 10.0,
            "price": 0.0,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False

    def test_invalid_transaction_type(self):
        """Invalid type should fail."""
        txn = {
            "type": "hold",  # Invalid
            "ticker": "VHY",
            "shares": 10.0,
            "price": 81.50,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False
        assert "'buy' or 'sell'" in msg.lower()

    def test_invalid_date_format(self):
        """Invalid date format should fail."""
        txn = {
            "type": "buy",
            "ticker": "VHY",
            "shares": 10.0,
            "price": 81.50,
            "date": "15/01/2026",  # Wrong format
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is False
        assert "date" in msg.lower()

    def test_case_insensitive_type(self):
        """Transaction type should be case insensitive."""
        txn = {
            "type": "BUY",
            "ticker": "VHY",
            "shares": 10.0,
            "price": 81.50,
            "date": "2026-01-15",
        }
        is_valid, msg = validate_transaction(txn)
        assert is_valid is True


class TestBuildHoldings:
    """Test holdings aggregation."""

    def test_single_buy_creates_holding(self):
        """Single buy creates one holding."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            }
        ]
        holdings = build_holdings(history)
        assert len(holdings) == 1
        assert holdings[0]["ticker"] == "VHY"
        assert holdings[0]["total_shares"] == 10.0
        assert holdings[0]["avg_cost"] == 81.50

    def test_multiple_buys_aggregate(self):
        """Multiple buys of same ticker aggregate correctly."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 80.00,
                "date": "2026-01-15",
            },
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 5.0,
                "price": 85.00,
                "date": "2026-02-01",
            },
        ]
        holdings = build_holdings(history)
        assert len(holdings) == 1
        assert holdings[0]["total_shares"] == 15.0
        # avg_cost = (10*80 + 5*85) / 15 = 1425 / 15 = 95
        assert holdings[0]["total_cost"] == 10 * 80 + 5 * 85

    def test_buy_then_sell_reduces_shares(self):
        """Sell transaction reduces shares."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            },
            {
                "type": "sell",
                "ticker": "VHY",
                "shares": 3.0,
                "price": 85.00,
                "date": "2026-02-01",
            },
        ]
        holdings = build_holdings(history)
        assert len(holdings) == 1
        assert holdings[0]["total_shares"] == 7.0
        # Remaining cost = original cost * (remaining shares / total bought)
        assert holdings[0]["total_cost"] == pytest.approx(
            81.50 * 10 * (7.0 / 10.0), abs=0.01
        )

    def test_fully_sold_position_excluded(self):
        """Position sold completely should not appear in holdings."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            },
            {
                "type": "sell",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 85.00,
                "date": "2026-02-01",
            },
        ]
        holdings = build_holdings(history)
        assert len(holdings) == 0

    def test_multiple_tickers_separate(self):
        """Different tickers should create separate holdings."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            },
            {
                "type": "buy",
                "ticker": "VAS",
                "shares": 5.0,
                "price": 99.00,
                "date": "2026-01-20",
            },
        ]
        holdings = build_holdings(history)
        assert len(holdings) == 2
        tickers = {h["ticker"] for h in holdings}
        assert tickers == {"VHY", "VAS"}

    def test_empty_history_returns_empty(self):
        """Empty transaction history should return empty holdings."""
        holdings = build_holdings([])
        assert holdings == []

    def test_invalid_transactions_skipped(self):
        """Invalid transactions should be skipped."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            },
            {
                "type": "buy",
                "ticker": "VAS",
                "shares": "invalid",  # Invalid
                "price": 99.00,
                "date": "2026-01-20",
            },
        ]
        holdings = build_holdings(history)
        # Only VHY should be included
        assert len(holdings) == 1
        assert holdings[0]["ticker"] == "VHY"

    def test_yfinance_ticker_suffix_added(self):
        """Ticker should get .AX suffix for yfinance."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            }
        ]
        holdings = build_holdings(history)
        assert holdings[0]["ticker_yf"] == "VHY.AX"

    def test_buy_tranches_created(self):
        """Each buy should be tracked in buy_tranches."""
        history = [
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 10.0,
                "price": 81.50,
                "date": "2026-01-15",
            },
            {
                "type": "buy",
                "ticker": "VHY",
                "shares": 5.0,
                "price": 85.00,
                "date": "2026-02-01",
            },
        ]
        holdings = build_holdings(history)
        assert len(holdings[0]["buy_tranches"]) == 2
        assert holdings[0]["buy_tranches"][0]["shares"] == 10.0
        assert holdings[0]["buy_tranches"][1]["shares"] == 5.0
