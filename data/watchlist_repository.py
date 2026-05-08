# data/watchlist_repository.py
import logging
import os
import pandas as pd
from datetime import datetime
from data.database import get_connection
from config.settings import DATA_CACHE_DIR

logger = logging.getLogger(__name__)

class WatchlistRepository:
    """
    Abstraction layer for watchlist data access.
    Now uses SQLite for persistence.
    """
    
    def load_watchlist(self) -> list[dict]:
        """Load all tickers from watchlist table."""
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT ticker, added_date, notes FROM watchlist")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

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
                    (item["ticker"].upper(), item["added_date"], item.get("notes", ""))
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save watchlist: {e}")
            conn.rollback()
        finally:
            conn.close()

    # ── History Methods (Still JSON-based as requested) ─────────────────────────

    def _get_history_path(self, ticker: str) -> str:
        cache_dir = os.path.join(DATA_CACHE_DIR, "watchlist_histories")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{ticker}_history.json")

    def load_history(self, ticker: str) -> list[dict]:
        import json
        path = self._get_history_path(ticker)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read history cache for {ticker}: {e}")
        return []

    def save_history(self, ticker: str, history: list[dict]) -> None:
        import json
        path = self._get_history_path(ticker)
        try:
            with open(path, "w") as f:
                json.dump(history, f)
        except Exception as e:
            logger.warning(f"Failed to write history cache for {ticker}: {e}")

    def delete_history(self, ticker: str) -> None:
        path = self._get_history_path(ticker)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to delete history cache for {ticker}: {e}")

    # ── Refresh Logic ──────────────────────────────────────────────────────────

    def fetch_and_save_history(self, ticker: str) -> None:
        import yfinance as yf
        try:
            df = yf.download(f"{ticker}.AX", period="max")
            if not df.empty:
                close_col = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
                close_col.index = pd.to_datetime(close_col.index)
                df_p = close_col.reset_index()
                df_p.columns = ["Date", "Close"]
                df_p["Date"] = df_p["Date"].dt.strftime("%Y-%m-%d")
                history = df_p.to_dict("records")
                self.save_history(ticker, history)
                logger.info(f"Successfully saved 1y history for {ticker}")
        except Exception as e:
            logger.error(f"Failed to fetch history for {ticker}: {e}")

    def refresh_all_histories(self) -> None:
        watchlist = self.load_watchlist()
        if not watchlist: return
        
        tickers_to_refresh = []
        for item in watchlist:
            ticker = item["ticker"]
            existing = self.load_history(ticker)
            if existing:
                first_date = pd.to_datetime(existing[0]["Date"])
                if (pd.Timestamp.now() - first_date).days < 1000:
                    tickers_to_refresh.append(ticker)
            else:
                tickers_to_refresh.append(ticker)
        
        if not tickers_to_refresh: return
        
        import yfinance as yf
        tickers_yf = [t + ".AX" for t in tickers_to_refresh]
        bulk_df = yf.download(tickers_yf, period="max", auto_adjust=True, progress=False)
        
        if bulk_df.empty: return
        
        from services.market.data_fetcher import extract_close
        for ticker in tickers_to_refresh:
            ticker_yf = ticker + ".AX"
            try:
                close = extract_close(bulk_df, ticker_yf)
                if close.empty: continue
                records = [
                    {"Date": d.strftime("%Y-%m-%d"), "Close": round(float(v), 4)}
                    for d, v in close.items() if v > 0
                ]
                if records:
                    self.save_history(ticker, records)
            except Exception as e:
                logger.warning(f"Failed to save history for {ticker}: {e}")

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
                (note, ticker.upper())
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
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, added_date) VALUES (?, ?)",
                (ticker, added_date)
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
            
        self.delete_history(ticker)
        return self.load_watchlist()
