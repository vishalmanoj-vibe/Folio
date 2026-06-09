# scratch/tests/test_prediction_service.py
import json
import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from data.database import init_db
from services.prediction_service import (
    _generate_cache_key,
    get_forecast,
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


def test_generate_cache_key():
    dates = ["2026-01-01", "2026-01-02"]
    key1 = _generate_cache_key(dates, "3mo")
    key2 = _generate_cache_key(dates, "3mo")
    assert key1 == key2
    assert isinstance(key1, str)
    assert len(key1) == 32  # MD5 length

    assert _generate_cache_key([], "3mo") == ""


def test_get_forecast_validation():
    # Empty inputs
    assert get_forecast([], [100.0], "3mo") == {}
    assert get_forecast(["2026-01-01"], [], "3mo") == {}


def test_get_forecast_cache_hit():
    dates = ["2026-01-01", "2026-01-02"]
    values = [100.0, 101.0]
    cache_key = _generate_cache_key(dates, "3mo")

    # Insert a mock result into the cache table in the temp test DB
    # We must use strftime('%Y-%m-%d %H:%M', 'now') to match prediction_service parsing format exactly
    from data.database import get_connection

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO predictions_cache (
                cache_key, dates, yhat, yhat_lower, yhat_upper, fitted_last, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M', 'now'))
        """,
            (
                cache_key,
                json.dumps(["2026-01-03"]),
                json.dumps([102.0]),
                json.dumps([101.0]),
                json.dumps([103.0]),
                101.0,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Call get_forecast. It should hit the cache and return the mock dict
    res = get_forecast(dates, values, "3mo")
    assert res is not None
    assert res["dates"] == ["2026-01-03"]
    assert res["yhat"] == [102.0]
    assert res["fitted_last"] == 101.0


@patch("services.prediction_service._PROPHET_AVAILABLE", False)
def test_get_forecast_prophet_disabled():
    dates = ["2026-01-01", "2026-01-02"]
    values = [100.0, 101.0]
    assert get_forecast(dates, values, "3mo") == {}


def test_get_forecast_read_only_miss():
    dates = ["2026-01-01", "2026-01-02"]
    values = [100.0, 101.0]
    # In read-only mode, a cache miss should return None immediately without fitting
    assert get_forecast(dates, values, "3mo", read_only=True) is None
