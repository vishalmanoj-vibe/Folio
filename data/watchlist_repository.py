# data/watchlist_repository.py
import logging
import os
from datetime import datetime

import pandas as pd

from config.settings import DATA_CACHE_DIR
from data.database import get_connection

logger = logging.getLogger(__name__)


class WatchlistRepository:
    """
    Abstraction layer for watchlist data access.
    Now uses SQLite for persistence.
    """

    def load_watchlist(self) -> list[dict]:
        """Load all tickers from watchlist table sorted by order_index and added_date."""
        conn = get_connection()
        try:
            cursor = conn.execute(
                "SELECT ticker, added_date, notes, order_index FROM watchlist ORDER BY order_index ASC, added_date ASC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def load_watchlist_holdings(self) -> list[dict]:
        """Returns synthetic holding dicts (avg_cost=0) for all watchlist tickers."""
        watchlist = self.load_watchlist()
        return [
            {
                "ticker": item["ticker"],
                "ticker_yf": item["ticker"] + ".AX",
                "total_shares": 0.0,
                "avg_cost": 0.0,
                "buy_tranches": [],
            }
            for item in watchlist
        ]

    def save_watchlist(self, watchlist: list[dict]) -> None:
        """
        Overwrite watchlist table.
        Note: Typically we use add/remove instead of full overwrite for relational.
        """
        conn = get_connection()
        try:
            conn.execute("DELETE FROM watchlist")
            for item in watchlist:
                conn.execute(
                    "INSERT INTO watchlist (ticker, added_date, notes) VALUES (?, ?, ?)",
                    (item["ticker"].upper(), item["added_date"], item.get("notes", "")),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save watchlist: {e}")
            conn.rollback()
        finally:
            conn.close()

    # ── History Methods (Relational) ───────────────────────────────────────────

    def fetch_and_save_history(self, ticker: str) -> None:
        """Fetch and persist history to SQLite via data_fetcher."""
        from services.market.data_fetcher import fetch_ticker_history

        fetch_ticker_history(ticker, "max")
        logger.info(f"Successfully ensured history for {ticker} in SQLite")

    def refresh_all_histories(self) -> None:
        """Bulk refresh all watchlist histories if stale via data_fetcher."""
        watchlist = self.load_watchlist()
        if not watchlist:
            return

        from services.market.data_fetcher import fetch_portfolio_history

        # fetch_portfolio_history internally checks for staleness and performs bulk downloads
        holdings_placeholders = [
            {"ticker": item["ticker"], "ticker_yf": item["ticker"] + ".AX"} for item in watchlist
        ]
        fetch_portfolio_history(holdings_placeholders, period="max")
        logger.info("Watchlist bulk refresh completed via data_fetcher")

    # ── Notes Methods ──────────────────────────────────────────────────────────

    def load_notes(self) -> dict:
        """Returns a dict of ticker -> note for all tickers in watchlist."""
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT ticker, notes FROM watchlist")
            return {row["ticker"]: row["notes"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def save_note(self, ticker: str, note: str) -> None:
        """Update the note for a specific ticker."""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE watchlist SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE ticker = ?",
                (note, ticker.upper()),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Membership Methods ─────────────────────────────────────────────────────

    def add_ticker(self, ticker: str) -> list[dict]:
        ticker = ticker.strip().upper()
        added_date = datetime.now().strftime("%Y-%m-%d")

        conn = get_connection()
        try:
            # Find next order index (append to bottom)
            row = conn.execute("SELECT MAX(order_index) FROM watchlist").fetchone()
            max_order = row[0] if row and row[0] is not None else -1
            new_order = max_order + 1

            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, added_date, order_index) VALUES (?, ?, ?)",
                (ticker, added_date, new_order),
            )
            conn.commit()
        finally:
            conn.close()

        self.fetch_and_save_history(ticker)
        return self.load_watchlist()

    def remove_ticker(self, ticker: str) -> list[dict]:
        ticker = ticker.strip().upper()
        conn = get_connection()
        try:
            conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
            conn.commit()
        finally:
            conn.close()

        return self.load_watchlist()

    def update_watchlist_order(self, ticker_order: list[str]) -> None:
        """Update the order_index of all tickers in the watchlist."""
        conn = get_connection()
        try:
            for index, ticker in enumerate(ticker_order):
                conn.execute(
                    "UPDATE watchlist SET order_index = ?, updated_at = CURRENT_TIMESTAMP WHERE ticker = ?",
                    (index, ticker.upper()),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update watchlist order: {e}")
            conn.rollback()
        finally:
            conn.close()
