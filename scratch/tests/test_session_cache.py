# scratch/tests/test_session_cache.py
import os
import sqlite3
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.database import get_connection, init_db
from services.market.session_cache import (
    backfill_session_cache,
    clear_old_caches,
    get_session_history,
    record_snapshot,
)


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Redirects database writes to a temporary test DB path."""
    test_db_path = "scratch/tests/test_portfolio.db"

    # Pre-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    with (
        patch("data.database.DB_PATH", test_db_path),
        patch("data.database._DB_INITIALIZED", False),
    ):
        init_db()  # Initialize schema
        yield

    # Post-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def test_record_snapshot_success():
    enriched_holdings = [
        {"ticker": "VAS", "last_price": 95.5},
        {"ticker": "VGS", "last_price": 100.0},
    ]

    record_snapshot(enriched_holdings)

    # Verify rows enqueued to SQLite
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM intraday_snapshots ORDER BY ticker").fetchall()
        assert len(rows) == 2
        assert rows[0]["ticker"] == "VAS"
        assert rows[0]["price"] == 95.5
        assert rows[1]["ticker"] == "VGS"
        assert rows[1]["price"] == 100.0
    finally:
        conn.close()


def test_record_snapshot_cooldown():
    enriched_holdings = [{"ticker": "VAS", "last_price": 95.5}]

    # 1. Record first snapshot
    record_snapshot(enriched_holdings)

    # 2. Record second snapshot immediately (should trigger cooldown and skip write)
    enriched_holdings_updated = [{"ticker": "VAS", "last_price": 96.0}]
    record_snapshot(enriched_holdings_updated)

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM intraday_snapshots").fetchall()
        # Should still only be 1 row since cooldown is 290s
        assert len(rows) == 1
        assert rows[0]["price"] == 95.5
    finally:
        conn.close()


def test_backfill_session_cache():
    now_syd = pd.Timestamp.now(tz="Australia/Sydney")
    syd_time1 = now_syd - pd.Timedelta(minutes=10)
    syd_time2 = now_syd - pd.Timedelta(minutes=5)

    tickers_data = {
        "VAS": pd.Series(
            [95.0, 95.5],
            index=[syd_time1, syd_time2],
        )
    }

    # Limit to syd_time1 so both points are captured
    backfill_session_cache(tickers_data, start_limit=syd_time1 - pd.Timedelta(seconds=1))

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM intraday_snapshots ORDER BY recorded_at").fetchall()
        assert len(rows) == 2
        assert rows[0]["ticker"] == "VAS"
        assert rows[0]["price"] == 95.0
        assert rows[1]["price"] == 95.5
    finally:
        conn.close()


@patch("data.cache_manager.get_intraday")
@patch("services.market.market_status.get_effective_session_context")
def test_get_session_history(mock_context, mock_get_intraday):
    mock_context.return_value = {
        "effective_date": pd.Timestamp("2026-06-09 00:00:00", tz="Australia/Sydney")
    }
    mock_get_intraday.return_value = pd.Series([95.0, 95.5])

    res = get_session_history("VAS")
    assert len(res) == 2
    mock_get_intraday.assert_called_once_with("VAS", "2026-06-09")


def test_clear_old_caches():
    # Insert one old row and one new row
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO intraday_snapshots (ticker, recorded_at, price, session_date)
            VALUES ('VAS', '2026-01-01 12:00:00', 90.0, '2026-01-01')
        """
        )
        conn.execute(
            """
            INSERT INTO intraday_snapshots (ticker, recorded_at, price, session_date)
            VALUES ('VAS', datetime('now'), 95.0, strftime('%Y-%m-%d', 'now'))
        """
        )
        conn.commit()
    finally:
        conn.close()

    # Clear anything older than 2 days
    clear_old_caches(keep_days=2)

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM intraday_snapshots").fetchall()
        # The 2026-01-01 snapshot should be deleted, leaving only the recent one
        assert len(rows) == 1
        assert rows[0]["price"] == 95.0
    finally:
        conn.close()
