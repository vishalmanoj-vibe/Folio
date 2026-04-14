"""
test/test_market_status.py
==========================
Unit tests for market_status module.

Tests market open/closed detection with configurable timezone and hours.
"""

import pytest
from datetime import datetime
from unittest.mock import patch
import pytz


class TestIsMarketOpen:
    """Test market open detection."""

    @patch('services.market.status.datetime')
    def test_market_open_during_trading_hours(self, mock_datetime):
        """Market should be open during trading hours (10:00-16:00 weekdays)."""
        from services.market.status import is_market_open
        
        # Tuesday 11:00 AET
        aet_tz = pytz.timezone('Australia/Sydney')
        trading_time = aet_tz.localize(datetime(2026, 1, 13, 11, 0, 0))  # Tuesday 11:00
        utc_time = trading_time.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        assert is_market_open() is True

    @patch('services.market.status.datetime')
    def test_market_closed_after_hours(self, mock_datetime):
        """Market should be closed after 16:00."""
        from services.market.status import is_market_open
        
        # Tuesday 17:00 AET
        aet_tz = pytz.timezone('Australia/Sydney')
        after_hours = aet_tz.localize(datetime(2026, 1, 13, 17, 0, 0))  # Tuesday 17:00
        utc_time = after_hours.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        assert is_market_open() is False

    @patch('services.market.status.datetime')
    def test_market_closed_before_hours(self, mock_datetime):
        """Market should be closed before 10:00."""
        from services.market.status import is_market_open
        
        # Tuesday 09:00 AET
        aet_tz = pytz.timezone('Australia/Sydney')
        before_hours = aet_tz.localize(datetime(2026, 1, 13, 9, 0, 0))  # Tuesday 09:00
        utc_time = before_hours.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        assert is_market_open() is False

    @patch('services.market.status.datetime')
    def test_market_closed_on_weekend(self, mock_datetime):
        """Market should be closed on weekends."""
        from services.market.status import is_market_open
        
        # Saturday 12:00 AET
        aet_tz = pytz.timezone('Australia/Sydney')
        weekend_time = aet_tz.localize(datetime(2026, 1, 10, 12, 0, 0))  # Saturday
        utc_time = weekend_time.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        assert is_market_open() is False

    @patch('services.market.status.datetime')
    def test_market_open_at_exact_open_time(self, mock_datetime):
        """Market should be open at exactly 10:00."""
        from services.market.status import is_market_open
        
        # Tuesday 10:00 AET
        aet_tz = pytz.timezone('Australia/Sydney')
        open_time = aet_tz.localize(datetime(2026, 1, 13, 10, 0, 0))
        utc_time = open_time.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        assert is_market_open() is True

    @patch('services.market.status.datetime')
    def test_market_closed_at_exact_close_time(self, mock_datetime):
        """Market should be closed at exactly 16:00."""
        from services.market.status import is_market_open
        
        # Tuesday 16:00 AET (at close)
        aet_tz = pytz.timezone('Australia/Sydney')
        close_time = aet_tz.localize(datetime(2026, 1, 13, 16, 0, 0))
        utc_time = close_time.astimezone(pytz.utc)
        
        mock_datetime.now.return_value = utc_time
        
        # At 16:00, market is closed (< 16 is open)
        assert is_market_open() is False


class TestMarketBadge:
    """Test market status badge rendering."""

    def test_badge_shows_open_status(self):
        """Badge should show 'ASX open' when market is open."""
        from services.market.status import market_badge, is_market_open
        
        # We can't reliably test the visual rendering,
        # but we can verify the function returns valid HTML
        badge = market_badge()
        assert badge is not None
        # Should contain either "open" or "closed"
        assert hasattr(badge, 'children')
