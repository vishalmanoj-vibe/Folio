# data/repository.py
import logging
from datetime import datetime, timedelta
import pandas as pd
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


class HistoryRepository:
    """
    Manages persistence of OHLC price histories in SQLite.
    """
    def __init__(self):
        init_db()

    def save_history(self, ticker: str, records: list[dict], period: str = None) -> None:
        """Bulk upsert OHLC records into price_history and update history_meta."""
        if not records:
            return
            
        ticker = ticker.upper()
        conn = get_connection()
        now_iso = datetime.now().isoformat()
        
        try:
            # 1. Upsert price records
            for r in records:
                # Normalise keys (handle both yfinance and internal formats)
                d = r.get("Date") or r.get("date")
                o = r.get("Open") or r.get("open_price") or r.get("open")
                h = r.get("High") or r.get("high_price") or r.get("high")
                l = r.get("Low") or r.get("low_price") or r.get("low")
                c = r.get("Close") or r.get("close_price") or r.get("close")
                v = r.get("Volume") or r.get("volume")
                dv = r.get("Dividends") or r.get("dividends") or 0.0
                
                if not d or c is None:
                    continue
                
                # Strip time if it's just a date string for consistency in historical charts
                if len(d) > 10 and " " in d:
                    d_clean = d.split(" ")[0]
                else:
                    d_clean = d
                    
                conn.execute('''
                    INSERT INTO price_history (ticker, date, open_price, high_price, low_price, close_price, volume, dividends, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, date) DO UPDATE SET
                        open_price = COALESCE(?, open_price),
                        high_price = COALESCE(?, high_price),
                        low_price = COALESCE(?, low_price),
                        close_price = ?,
                        volume = COALESCE(?, volume),
                        dividends = COALESCE(?, dividends),
                        fetched_at = ?
                ''', (ticker, d_clean, o, h, l, c, v, dv, now_iso, o, h, l, c, v, dv, now_iso))
            
            # 2. Update metadata
            valid_dates = [r.get("Date") or r.get("date") for r in records if (r.get("Date") or r.get("date"))]
            if not valid_dates:
                return

            first_date = min(valid_dates).split(" ")[0]
            last_date = max(valid_dates).split(" ")[0]
            
            conn.execute('''
                INSERT INTO history_meta (ticker, first_date, last_date, last_fetched, period)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    first_date = CASE WHEN ? < first_date THEN ? ELSE first_date END,
                    last_date = CASE WHEN ? > last_date THEN ? ELSE last_date END,
                    last_fetched = ?,
                    period = COALESCE(?, period)
            ''', (ticker, first_date, last_date, now_iso, period, first_date, first_date, last_date, last_date, now_iso, period))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save history for {ticker}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def load_history(self, ticker: str, from_date: str = None, to_date: str = None) -> list[dict]:
        """Fetch historical records for a ticker within an optional date range."""
        ticker = ticker.upper()
        conn = get_connection()
        try:
            query = "SELECT date, open_price, high_price, low_price, close_price, volume, dividends FROM price_history WHERE ticker = ?"
            params = [ticker]
            
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
                
            query += " ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return []
                
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Dividends"]
            return df.to_dict("records")
        finally:
            conn.close()

    def load_close_series(self, ticker: str, from_date: str = None) -> pd.Series:
        """Efficiently fetch only the Close price series for a ticker."""
        ticker = ticker.upper()
        conn = get_connection()
        try:
            query = "SELECT date, close_price FROM price_history WHERE ticker = ?"
            params = [ticker]
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
            query += " ORDER BY date ASC"
            
            df = pd.read_sql_query(query, conn, params=params)
            if df.empty:
                return pd.Series(dtype=float)
            
            df["date"] = pd.to_datetime(df["date"])
            return df.set_index("date")["close_price"]
        finally:
            conn.close()

    def get_latest_prices(self, tickers: list[str]) -> dict:
        """
        Retrieves the latest price, prev close, and day range for a list of tickers.
        Efficiently fetches only the last 2 records per ticker from price_history.
        """
        if not tickers: return {}
        tickers = [t.upper() for t in tickers]
        conn = get_connection()
        try:
            placeholders = ",".join(["?"] * len(tickers))
            # We fetch the latest 2 records for each ticker to determine last vs prev
            query = f"""
                SELECT ticker, date, close_price, high_price, low_price
                FROM (
                    SELECT ticker, date, close_price, high_price, low_price,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                    FROM price_history
                    WHERE ticker IN ({placeholders})
                )
                WHERE rn <= 2
            """
            df = pd.read_sql_query(query, conn, params=tickers)
            if df.empty: return {}

            results = {}
            for ticker, group in df.groupby("ticker"):
                group = group.sort_values("date", ascending=False)
                latest = group.iloc[0]
                prev = group.iloc[1] if len(group) > 1 else latest
                
                results[ticker] = {
                    "last_price": float(latest["close_price"]),
                    "prev_close": float(prev["close_price"]),
                    "day_high": float(latest["high_price"]),
                    "day_low": float(latest["low_price"])
                }
            return results
        finally:
            conn.close()

    def get_meta(self, ticker: str) -> dict | None:
        """Retrieve metadata for a ticker's history."""
        ticker = ticker.upper()
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM history_meta WHERE ticker = ?", (ticker,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def is_stale(self, ticker: str, requested_period: str = "max") -> bool:
        """
        Determine if history needs a refresh based on market status and requested depth.
        Threshold: 5 minutes if market is open, 24 hours if closed.
        Also triggers if stored history does not cover the requested period.
        """
        from services.market.market_status import is_market_open
        from core.engine.utils import get_period_cutoff
        
        meta = self.get_meta(ticker)
        if not meta or not meta.get("last_fetched"):
            return True
            
        # 1. Recency check
        try:
            last_fetched = datetime.fromisoformat(meta["last_fetched"])
            age = datetime.now() - last_fetched
            
            # Recency threshold: Daily history only needs once-per-day refresh
            # Intraday data is handled separately by fetch_live.
            recency_limit = 86400 # 24 hours
            if age.total_seconds() > recency_limit:
                return True
        except Exception:
            return True

        # 2. Depth check
        stored_first = meta.get("first_date")
        if not stored_first:
            return True
            
        cutoff = get_period_cutoff(requested_period)
        if cutoff:
            cutoff_str = cutoff.strftime("%Y-%m-%d")
            if stored_first > cutoff_str:
                logger.debug(f"Depth stale for {ticker}: stored_first({stored_first}) > cutoff({cutoff_str})")
                return True
        else:
            # Requested period is "max" (Since purchase)
            # Threshold: If we have < 220 days, it's definitely stale for technicals,
            # UNLESS we have already fetched the full available 'max' history.
            stored_last = meta.get("last_date")
            if stored_first and stored_last:
                try:
                    d1 = datetime.strptime(stored_first, "%Y-%m-%d")
                    d2 = datetime.strptime(stored_last, "%Y-%m-%d")
                    days = (d2 - d1).days
                    if days < 220:
                        # Check if we already tried a 'max' fetch
                        if meta.get("period") != "max":
                            logger.info(f"Depth stale for {ticker}: requested max but only {days} days stored. Attempting full history recovery.")
                            return True
                except Exception:
                    pass
                
        return False

    def has_dividends(self, ticker: str) -> bool:
        """Check if any non-zero dividends are recorded for this ticker."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM price_history WHERE ticker = ? AND dividends > 0",
                (ticker.upper(),)
            ).fetchone()
            return row["count"] > 0
        except:
            return False
        finally:
            conn.close()

    def delete_old_records(self, days_to_keep: int = 730) -> None:
        """Cleanup price history records older than the retention limit."""
        conn = get_connection()
        try:
            cutoff = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            cursor = conn.execute("DELETE FROM price_history WHERE date < ?", (cutoff,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} stale history records older than {cutoff}")
        except Exception as e:
            logger.error(f"History cleanup failed: {e}")
            conn.rollback()
        finally:
            conn.close()
