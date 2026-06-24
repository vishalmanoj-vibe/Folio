import os
import sqlite3
from collections.abc import Generator
from unittest.mock import patch

import pytest

from data.database import enqueue_task, get_connection, init_db


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Sets up a temporary isolated SQLite database file for testing, whitelisting tables and schemas."""
    test_db_path: str = "scratch/tests/test_portfolio.db"

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
        init_db()  # Run full database initialization
        yield

    # Post-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def test_init_db_success() -> None:
    """Assert init_db initializes the complete database schema with index indexes."""
    test_db_path: str = "scratch/tests/test_portfolio.db"

    with patch("data.database.DB_PATH", test_db_path):
        conn: sqlite3.Connection = get_connection()
        try:
            # Query the master table list from SQLite
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables: list[str] = [row["name"] for row in cursor.fetchall()]

            assert "transactions" in tables
            assert "assets" in tables
            assert "watchlist" in tables
            assert "etf_metadata" in tables
            assert "price_history" in tables
            assert "worker_tasks" in tables
            assert "signal_results" in tables
        finally:
            conn.close()


def test_get_connection_pragmas() -> None:
    """Assert database connection is successfully configured with concurrency WAL and busy timeouts."""
    test_db_path: str = "scratch/tests/test_portfolio.db"

    with patch("data.database.DB_PATH", test_db_path):
        conn: sqlite3.Connection = get_connection()
        try:
            # Check journal mode is set to Write-Ahead Logging (WAL)
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert journal_mode.upper() == "WAL"

            # Check busy timeout is configured correctly
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            assert busy_timeout == 5000
        finally:
            conn.close()


def test_enqueue_task_success() -> None:
    """Assert worker tasks enqueue cleanly and return valid UUID task IDs."""
    test_db_path: str = "scratch/tests/test_portfolio.db"

    with patch("data.database.DB_PATH", test_db_path):
        task_id: str = enqueue_task(
            task_type="fetch_history", payload={"ticker": "VAS", "period": "max"}, priority=7
        )

        # Verify task enqueued correctly
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID length

        conn: sqlite3.Connection = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM worker_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            assert row is not None
            assert row["task_type"] == "fetch_history"
            assert "VAS" in row["payload"]
            assert row["priority"] == 7
            assert row["status"] == "pending"
        finally:
            conn.close()


# ── PortfolioRepository Tests ──────────────────────────────────────────────


def test_portfolio_repository_transactions() -> None:
    """Assert transactions load, save, and append correctly in SQLite."""
    from data.repository import PortfolioRepository

    repo = PortfolioRepository()

    # Save transactions with explicit IDs
    txns = [
        {
            "id": 42,
            "type": "buy",
            "ticker": "VAS",
            "shares": 10.0,
            "price": 90.0,
            "date": "2026-01-01",
        },
        {
            "id": 100,
            "type": "sell",
            "ticker": "VAS",
            "shares": 5.0,
            "price": 95.0,
            "date": "2026-01-02",
        },
    ]
    repo.save_transactions(txns)

    loaded = repo.load_transactions()
    assert len(loaded) == 2
    assert loaded[0]["id"] == 42
    assert loaded[0]["ticker"] == "VAS"
    assert loaded[0]["type"] == "buy"
    assert loaded[0]["shares"] == 10.0
    assert loaded[1]["id"] == 100

    # Append transaction (should auto-increment ID to 101 or higher)
    new_txn = {"type": "buy", "ticker": "VGS", "shares": 20.0, "price": 100.0, "date": "2026-01-03"}
    loaded_after = repo.append_transaction(new_txn)
    assert len(loaded_after) == 3
    assert loaded_after[2]["ticker"] == "VGS"
    assert loaded_after[2]["id"] is not None
    assert loaded_after[2]["id"] > 100


def test_portfolio_repository_metadata() -> None:
    """Assert onboarding state and API key stores update and fetch correctly."""
    from data.repository import PortfolioRepository

    repo = PortfolioRepository()

    # Onboarding
    assert repo.is_onboarding_completed() is False
    repo.set_onboarding_completed(True)
    assert repo.is_onboarding_completed() is True

    # Gemini API Key
    assert repo.get_gemini_api_key() is None
    repo.set_gemini_api_key("test_key")
    assert repo.get_gemini_api_key() == "test_key"


def test_portfolio_repository_assets() -> None:
    """Assert asset records load and upsert securely."""
    from data.repository import PortfolioRepository

    repo = PortfolioRepository()

    assert repo.get_asset("VAS") is None
    repo.upsert_asset("VAS", name="Vanguard Australian Shares", category="Equity", market="ASX")

    asset = repo.get_asset("VAS")
    assert asset is not None
    assert asset["name"] == "Vanguard Australian Shares"
    assert asset["category"] == "Equity"
    assert asset["market"] == "ASX"


# ── HistoryRepository Tests ──────────────────────────────────────────────────


def test_history_repository() -> None:
    """Assert price histories, close series, latest pricing and metadata persist properly."""
    import pandas as pd

    from data.repository import HistoryRepository

    repo = HistoryRepository()

    # Save history
    records = [
        {
            "date": "2026-01-01",
            "open": 90.0,
            "high": 92.0,
            "low": 89.0,
            "close": 91.0,
            "volume": 1000,
            "dividends": 0.5,
        },
        {
            "date": "2026-01-02",
            "open": 91.0,
            "high": 93.0,
            "low": 90.0,
            "close": 92.0,
            "volume": 1200,
            "dividends": 0.0,
        },
    ]
    repo.save_history("VAS", records, period="max")

    loaded = repo.load_history("VAS")
    assert len(loaded) == 2
    assert loaded[0]["Close"] == 91.0
    assert loaded[0]["Dividends"] == 0.5

    # Load close series
    series = repo.load_close_series("VAS")
    assert len(series) == 2
    assert series.iloc[0] == 91.0

    # Get latest prices
    prices = repo.get_latest_prices(["VAS"])
    assert "VAS" in prices
    assert prices["VAS"]["last_price"] == 92.0
    assert prices["VAS"]["prev_close"] == 91.0

    # Get meta
    meta = repo.get_meta("VAS")
    assert meta is not None
    assert meta["period"] == "max"

    # Staleness check
    assert repo.is_stale("VAS", "max") is False
    assert repo.is_stale("VAS", "5d") is False

    # Has dividends
    assert repo.has_dividends("VAS") is True
    assert repo.has_dividends("VGS") is False

    # Delete old records
    repo.delete_old_records(days_to_keep=1)
    assert len(repo.load_history("VAS")) == 0


# ── WatchlistRepository Tests ────────────────────────────────────────────────


def test_watchlist_repository() -> None:
    """Assert watchlist membership, notes, ordering, and synthetic holdings update safely."""
    from unittest.mock import patch

    from data.watchlist_repository import WatchlistRepository

    repo = WatchlistRepository()

    # Save and Load watchlist
    items = [
        {"ticker": "VAS", "added_date": "2026-01-01", "notes": "Holdings leader"},
        {"ticker": "VGS", "added_date": "2026-01-02"},
    ]
    repo.save_watchlist(items)

    watchlist = repo.load_watchlist()
    assert len(watchlist) == 2
    assert watchlist[0]["ticker"] == "VAS"

    # Load watchlist holdings
    holdings = repo.load_watchlist_holdings()
    assert len(holdings) == 2
    assert holdings[0]["ticker"] == "VAS"
    assert holdings[0]["ticker_yf"] == "VAS.AX"
    assert holdings[0]["avg_cost"] == 0.0

    # Notes methods
    notes = repo.load_notes()
    assert notes["VAS"] == "Holdings leader"

    repo.save_note("VAS", "Updated note")
    assert repo.load_notes()["VAS"] == "Updated note"

    # Membership methods (Mock history fetch to isolate DB)
    with patch("data.watchlist_repository.WatchlistRepository.fetch_and_save_history"):
        repo.add_ticker("A200")

    watchlist = repo.load_watchlist()
    assert len(watchlist) == 3
    assert any(w["ticker"] == "A200" for w in watchlist)

    repo.remove_ticker("A200")
    watchlist = repo.load_watchlist()
    assert len(watchlist) == 2
    assert not any(w["ticker"] == "A200" for w in watchlist)

    # Order update
    repo.update_watchlist_order(["VGS", "VAS"])
    watchlist = repo.load_watchlist()
    assert watchlist[0]["ticker"] == "VGS"  # Reordered correctly sorted by order_index
