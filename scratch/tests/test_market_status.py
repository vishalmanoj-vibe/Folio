# scratch/tests/test_market_status.py
from unittest.mock import patch

import pandas as pd
import pytest

from services.market.market_status import (
    get_effective_session_context,
    get_previous_trading_session_start,
    is_market_open,
    time_until_market_open,
)

# ── is_market_open Tests ─────────────────────────────────────────────────────


@patch("pandas.Timestamp.now")
def test_is_market_open_weekend(mock_now):
    # Saturday 12:00 PM
    mock_now.return_value = pd.Timestamp("2026-06-13 12:00:00", tz="Australia/Sydney")
    assert not is_market_open()


@patch("pandas.Timestamp.now")
def test_is_market_open_holiday(mock_now):
    # Good Friday 2026 was April 3
    mock_now.return_value = pd.Timestamp("2026-04-03 12:00:00", tz="Australia/Sydney")
    assert not is_market_open()


@patch("pandas.Timestamp.now")
def test_is_market_open_active_hours(mock_now):
    # Wednesday 12:00 PM
    mock_now.return_value = pd.Timestamp("2026-06-10 12:00:00", tz="Australia/Sydney")
    assert is_market_open()

    # Wednesday 8:00 AM (Closed)
    mock_now.return_value = pd.Timestamp("2026-06-10 08:00:00", tz="Australia/Sydney")
    assert not is_market_open()

    # Wednesday 4:05 PM (Open if include_auction=True, Closed if False)
    mock_now.return_value = pd.Timestamp("2026-06-10 16:05:00", tz="Australia/Sydney")
    assert is_market_open(include_auction=True)
    assert not is_market_open(include_auction=False)


# ── get_previous_trading_session_start Tests ─────────────────────────────────


def test_get_previous_trading_session_start_midweek():
    # Wednesday -> previous trading session starts on Tuesday at 15:00
    base_date = pd.Timestamp("2026-06-10 12:00:00", tz="Australia/Sydney")
    prev = get_previous_trading_session_start(relative_to=base_date)
    assert prev == pd.Timestamp("2026-06-09 15:00:00", tz="Australia/Sydney")


def test_get_previous_trading_session_start_weekend():
    # Monday -> previous trading session starts on Friday at 15:00
    base_date = pd.Timestamp("2026-06-15 12:00:00", tz="Australia/Sydney")
    prev = get_previous_trading_session_start(relative_to=base_date)
    assert prev == pd.Timestamp("2026-06-12 15:00:00", tz="Australia/Sydney")


# ── get_effective_session_context Tests ──────────────────────────────────────


@patch("pandas.Timestamp.now")
def test_get_effective_session_context_active(mock_now):
    # Wednesday 12:00 PM (Trading Day, open)
    mock_now.return_value = pd.Timestamp("2026-06-10 12:00:00", tz="Australia/Sydney")
    ctx = get_effective_session_context()
    assert ctx["effective_date"] == pd.Timestamp("2026-06-10", tz="Australia/Sydney")
    assert ctx["anchor_date"] == pd.Timestamp("2026-06-09", tz="Australia/Sydney")
    assert ctx["is_live"] is True


@patch("pandas.Timestamp.now")
def test_get_effective_session_context_morning(mock_now):
    # Wednesday 8:00 AM (Trading Day, before market open)
    # Effective should be Tuesday (June 9), anchor should be Friday (June 5) because Monday (June 8) is King's Birthday holiday
    mock_now.return_value = pd.Timestamp("2026-06-10 08:00:00", tz="Australia/Sydney")
    ctx = get_effective_session_context()
    assert ctx["effective_date"] == pd.Timestamp("2026-06-09", tz="Australia/Sydney")
    assert ctx["anchor_date"] == pd.Timestamp("2026-06-05", tz="Australia/Sydney")
    assert ctx["is_live"] is False


@patch("pandas.Timestamp.now")
def test_get_effective_session_context_weekend(mock_now):
    # Sunday -> effective should be Friday, anchor should be Thursday
    mock_now.return_value = pd.Timestamp("2026-06-14 12:00:00", tz="Australia/Sydney")
    ctx = get_effective_session_context()
    assert ctx["effective_date"] == pd.Timestamp("2026-06-12", tz="Australia/Sydney")
    assert ctx["anchor_date"] == pd.Timestamp("2026-06-11", tz="Australia/Sydney")
    assert ctx["is_live"] is False


# ── time_until_market_open Tests ─────────────────────────────────────────────


@patch("pandas.Timestamp.now")
def test_time_until_market_open_midweek_before(mock_now):
    # Wednesday 9:00 AM -> 55 minutes until 9:55 AM = 3300 seconds
    mock_now.return_value = pd.Timestamp("2026-06-10 09:00:00", tz="Australia/Sydney")
    assert time_until_market_open() == 3300.0


@patch("pandas.Timestamp.now")
def test_time_until_market_open_during_open(mock_now):
    # Wednesday 12:00 PM -> 0 seconds
    mock_now.return_value = pd.Timestamp("2026-06-10 12:00:00", tz="Australia/Sydney")
    assert time_until_market_open() == 0.0


@patch("pandas.Timestamp.now")
def test_time_until_market_open_weekend(mock_now):
    # Saturday 12:00 PM -> next target is Monday 9:55 AM
    # Sat 12:00 to Sun 12:00 = 86400s
    # Sun 12:00 to Mon 09:55 = 78900s
    # Total = 165300s
    mock_now.return_value = pd.Timestamp("2026-06-13 12:00:00", tz="Australia/Sydney")
    assert time_until_market_open() == 165300.0
