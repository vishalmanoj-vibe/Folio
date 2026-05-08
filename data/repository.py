# data/repository.py
import logging
from data.database import get_connection, init_db

logger = logging.getLogger(__name__)

class PortfolioRepository:
    """
    Abstraction layer for portfolio data access.
    Now uses SQLite storage for improved performance and reliability.
    """
    
    def __init__(self):
        # Ensure database is initialised on startup
        init_db()

    def load_transactions(self) -> list[dict]:
        """Load all transactions from the SQLite database."""
        conn = get_connection()
        try:
            cursor = conn.execute(
                "SELECT type, ticker, shares, price, date FROM transactions ORDER BY date ASC, id ASC"
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to load transactions: {e}")
            return []
        finally:
            conn.close()

    def save_transactions(self, history: list[dict]) -> None:
        """Overwrite the database with full transaction history."""
        conn = get_connection()
        try:
            # Clear existing data first
            conn.execute("DELETE FROM transactions")
            
            # Re-insert all rows
            for txn in history:
                conn.execute(
                    """
                    INSERT INTO transactions (type, ticker, shares, price, date) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(txn["type"]).lower(),
                        str(txn["ticker"]).upper(),
                        float(txn["shares"]),
                        float(txn["price"]),
                        str(txn["date"]),
                    )
                )
            conn.commit()
            logger.info(f"Overwrote database with {len(history)} transactions")
        except Exception as e:
            logger.error(f"Failed to save transactions: {e}")
            conn.rollback()
        finally:
            conn.close()

    def append_transaction(self, txn: dict) -> list[dict]:
        """Append a single transaction and return the updated history."""
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO transactions (type, ticker, shares, price, date) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(txn["type"]).lower(),
                    str(txn["ticker"]).upper(),
                    float(txn["shares"]),
                    float(txn["price"]),
                    str(txn["date"]),
                )
            )
            conn.commit()
            logger.info(
                f"Transaction saved to DB: {txn['type']} {txn['shares']} {txn['ticker']}"
            )
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            conn.rollback()
        finally:
            conn.close()
        return self.load_transactions()

    # ── Asset (Ticker Master) Methods ──────────────────────────────────────────

    def get_asset(self, ticker: str) -> dict | None:
        """Retrieve a cached asset record (name, category, etc.)."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM assets WHERE ticker = ?", 
                (ticker.upper(),)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def upsert_asset(self, ticker: str, name: str = None, category: str = None, market: str = None) -> None:
        """Insert or update a ticker master record."""
        ticker = ticker.upper()
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO assets (ticker, name, category, market, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(ticker) DO UPDATE SET
                    name = COALESCE(?, name),
                    category = COALESCE(?, category),
                    market = COALESCE(?, market),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (ticker, name, category, market, name, category, market)
            )
            conn.commit()
        finally:
            conn.close()
