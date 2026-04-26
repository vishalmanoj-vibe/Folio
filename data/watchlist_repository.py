# data/watchlist_repository.py
import logging
import os
import pandas as pd
from datetime import datetime
from config.settings import WATCHLIST_CSV_PATH

logger = logging.getLogger(__name__)

class WatchlistRepository:
    """
    Abstraction layer for watchlist data access.
    """
    
    def load_watchlist(self) -> list[dict]:
        """Load all tickers from watchlist CSV."""
        if not os.path.exists(WATCHLIST_CSV_PATH):
            return []
        try:
            # Handle empty files or reading errors gracefully
            if os.path.getsize(WATCHLIST_CSV_PATH) == 0:
                return []
                
            df = pd.read_csv(WATCHLIST_CSV_PATH)
            if df.empty:
                return []
                
            # Normalize column names to lowercase
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            if "ticker" not in df.columns:
                logger.warning(f"Watchlist CSV at {WATCHLIST_CSV_PATH} is missing 'ticker' column.")
                return []
                
            df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
            return df.to_dict("records")
        except Exception as e:
            logger.error(f"Failed to load watchlist from {WATCHLIST_CSV_PATH}: {e}")
            return []

    def save_watchlist(self, watchlist: list[dict]) -> None:
        """Overwrite watchlist storage using an atomic write pattern."""
        try:
            df = pd.DataFrame(watchlist)
            if not df.empty:
                # Standardize column names for the CSV
                df.columns = [str(c).capitalize() for c in df.columns]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(WATCHLIST_CSV_PATH), exist_ok=True)
            
            # Atomic write: Write to .tmp first then rename
            tmp_path = WATCHLIST_CSV_PATH + ".tmp"
            df.to_csv(tmp_path, index=False)
            os.replace(tmp_path, WATCHLIST_CSV_PATH)
            
            logger.info("Successfully saved %d tickers to watchlist", len(watchlist))
        except Exception as e:
            logger.error(f"CRITICAL: Failed to save watchlist to {WATCHLIST_CSV_PATH}: {e}")

    def _get_history_path(self, ticker: str) -> str:
        cache_dir = os.path.join(os.path.dirname(WATCHLIST_CSV_PATH), "cache", "watchlist_histories")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{ticker}_history.json")

    def load_history(self, ticker: str) -> list[dict]:
        """Load persistent history for a ticker from JSON cache."""
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
        """Save history for a ticker to JSON cache persistently."""
        import json
        path = self._get_history_path(ticker)
        try:
            with open(path, "w") as f:
                json.dump(history, f)
        except Exception as e:
            logger.warning(f"Failed to write history cache for {ticker}: {e}")

    def delete_history(self, ticker: str) -> None:
        """Delete history cache for a ticker when removed from watchlist."""
        path = self._get_history_path(ticker)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to delete history cache for {ticker}: {e}")

    def fetch_and_save_history(self, ticker: str) -> None:
        """Fetch 1y history from yfinance and save to disk."""
        import yfinance as yf
        try:
            df = yf.download(f"{ticker}.AX", period="max")
            if not df.empty:
                # Handle single ticker columns properly
                close_col = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
                close_col.index = pd.to_datetime(close_col.index)
                
                # Format exactly like history_data
                df_p = close_col.reset_index()
                df_p.columns = ["Date", "Close"]
                # Convert Date to string
                df_p["Date"] = df_p["Date"].dt.strftime("%Y-%m-%d")
                history = df_p.to_dict("records")
                self.save_history(ticker, history)
                logger.info(f"Successfully saved 1y history for {ticker}")
            else:
                logger.warning(f"No history returned from yfinance for {ticker}")
        except Exception as e:
            logger.error(f"Failed to fetch history for {ticker}: {e}")

    def refresh_all_histories(self) -> None:
        """
        Re-fetch full history (period=max) for all tickers
        currently in the watchlist and overwrite their cache files.
        Called once on startup if cache appears to be short.
        """
        watchlist = self.load_watchlist()
        if not watchlist:
            return
        for item in watchlist:
            ticker = item["ticker"]
            existing = self.load_history(ticker)
            if existing:
                import pandas as pd
                first_date = pd.to_datetime(existing[0]["Date"])
                age_days = (pd.Timestamp.now() - first_date).days
                # Only refresh if cache is less than 3 years old
                # (meaning it was fetched with period="1y" originally)
                if age_days < 1000:
                    logger.info(
                        f"Refreshing {ticker} cache "
                        f"(only {age_days} days of history)"
                    )
                self.fetch_and_save_history(ticker)
            else:
                self.fetch_and_save_history(ticker)

    def load_notes(self) -> dict:
        import json
        path = os.path.join(
            os.path.dirname(WATCHLIST_CSV_PATH), "cache", "watchlist_notes.json"
        )
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_note(self, ticker: str, note: str) -> None:
        import json
        path = os.path.join(
            os.path.dirname(WATCHLIST_CSV_PATH), "cache", "watchlist_notes.json"
        )
        notes = self.load_notes()
        notes[ticker] = note
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(notes, f)
        except Exception as e:
            logger.warning(f"Failed to save note for {ticker}: {e}")

    def add_ticker(self, ticker: str) -> list[dict]:
        """Add a ticker to the watchlist and return updated list."""
        watchlist = self.load_watchlist()
        ticker = ticker.strip().upper()
        
        # Check if already exists
        if any(item['ticker'] == ticker for item in watchlist):
            return watchlist
            
        new_item = {
            "ticker": ticker,
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }
        watchlist.append(new_item)
        self.save_watchlist(watchlist)
        self.fetch_and_save_history(ticker)
        return watchlist

    def remove_ticker(self, ticker: str) -> list[dict]:
        """Remove a ticker from the watchlist."""
        watchlist = self.load_watchlist()
        ticker = ticker.strip().upper()
        
        filtered = [item for item in watchlist if item['ticker'] != ticker]
        if len(filtered) != len(watchlist):
            self.save_watchlist(filtered)
            self.delete_history(ticker)
            logger.info(f"Removed {ticker} from watchlist")
        return filtered
