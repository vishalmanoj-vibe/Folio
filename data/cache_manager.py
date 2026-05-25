# data/cache_manager.py
import logging
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache
from data.database import get_connection

logger = logging.getLogger(__name__)

# ── Market Prices (Live Snapshots) ───────────────────────────────────────────

def get_live_prices(tickers: list[str]) -> dict:
    """
    Retrieve the current live price snapshot for a list of tickers.
    Returns a dict keyed by ticker.
    """
    from config.settings import REFRESH_INTERVAL
    if not tickers:
        return {}
        
    conn = get_connection()
    try:
        placeholders = ",".join(["?"] * len(tickers))
        cursor = conn.execute(
            f"SELECT * FROM market_prices WHERE ticker IN ({placeholders})",
            [t.upper() for t in tickers]
        )
        rows = cursor.fetchall()
        result = {row["ticker"]: dict(row) for row in rows}
        
        # Check freshness
        needs_refresh = False
        is_missing = False
        now = datetime.now()
        refresh_limit_sec = REFRESH_INTERVAL / 1000.0
        
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker not in result:
                needs_refresh = True
                is_missing = True
                break
            
            fetched_at_str = result[ticker].get("fetched_at")
            if fetched_at_str:
                try:
                    fetched_at = datetime.fromisoformat(fetched_at_str)
                    if (now - fetched_at).total_seconds() > refresh_limit_sec:
                        needs_refresh = True
                        break
                except ValueError:
                    needs_refresh = True
                    break
            else:
                needs_refresh = True
                break
        
        if needs_refresh:
            from services.market.market_status import is_market_open
            if is_missing or is_market_open(include_auction=True):
                # Synchronous fetch when stale
                try:
                    from services.market.data_fetcher import fetch_live
                    from data.repository import PortfolioRepository
                    
                    logger.info("Live prices stale, performing synchronous fetch...")
                    repo = PortfolioRepository()
                    txns = repo.load_transactions()
                    from core.engine.portfolio_engine import build_holdings
                    holdings = build_holdings(txns)
                    
                    if holdings:
                        fetch_live(holdings, record_snapshots=True)
                        # CRITICAL: Close and reopen connection so WAL-committed data is visible.
                        # Reusing the same connection returns stale data from the snapshot
                        # taken at connection-open time, before fetch_live() wrote new records.
                        conn.close()
                        conn = get_connection()
                        cursor = conn.execute(
                            f"SELECT * FROM market_prices WHERE ticker IN ({placeholders})",
                            [t.upper() for t in tickers]
                        )
                        rows = cursor.fetchall()
                        result = {row["ticker"]: dict(row) for row in rows}
                except Exception as e:
                    logger.error(f"Synchronous live price fetch failed: {e}")
        
        # ── Merge with latest OHLC from price_history ──
        # These fields are NOT in market_prices per user rules, so we fetch them here.
        from data.repository import HistoryRepository
        h_repo = HistoryRepository()
        latest_ohlc = h_repo.get_latest_prices(tickers)
        
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in result:
                ohlc = latest_ohlc.get(ticker, {})
                result[ticker].update(ohlc)
            
        return result
    finally:
        conn.close()

def save_live_prices(holdings: list[dict]):
    """Save enriched holdings to the market_prices table."""
    if not holdings:
        return
        
    conn = get_connection()
    fetched_at = datetime.now().isoformat()
    try:
        for h in holdings:
            conn.execute('''\
                INSERT OR REPLACE INTO market_prices (
                    ticker, last_price, day_chg, day_chg_pct, day_pnl, mkt_value, pnl, pnl_pct, 
                    annual_div, realized_div, div_yield, div_frequency, 
                    last_div_amount, last_div_date, next_div_date, payout_date, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                h["ticker"].upper(), h.get("last_price"), h.get("day_chg"), h.get("day_chg_pct"), h.get("day_pnl"),
                h.get("mkt_value"), h.get("pnl"), h.get("pnl_pct"), h.get("annual_div"),
                h.get("realized_div"), h.get("div_yield"), h.get("div_frequency"),
                h.get("last_div_amount"), h.get("last_div_date"), h.get("next_div_date"), h.get("payout_date"),
                fetched_at
            ))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save live prices: {e}")
    finally:
        conn.close()


# ── Intraday Snapshots ───────────────────────────────────────────────────────

def get_intraday(ticker: str, since_at: str) -> pd.Series:
    """
    Retrieve intraday price history for a ticker starting from a specific timestamp.
    Returns a pandas Series indexed by recorded_at.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT recorded_at, price FROM intraday_snapshots WHERE ticker = ? AND recorded_at >= ? ORDER BY recorded_at ASC",
            (ticker.upper(), since_at)
        )
        rows = cursor.fetchall()
        if not rows:
            return pd.Series(dtype=float)
            
        data = {pd.to_datetime(row["recorded_at"]): row["price"] for row in rows}
        return pd.Series(data)
    finally:
        conn.close()

# ── Historical Data ─────────────────────────────────────────────────────────

def get_history(ticker: str, period: str) -> list[dict]:
    """
    Retrieve historical data from SQLite.
    If stale or missing, queues a fetch task (logged for now).
    """
    from data.repository import HistoryRepository
    from core.engine.utils import get_period_cutoff
    
    ticker = ticker.upper()
    repo = HistoryRepository()
    
    # Check if stale or missing
    if repo.is_stale(ticker, requested_period=period):
        logger.debug(f"History for {ticker} is stale or missing for period {period}. Refresh suggested.")
        # In a real worker architecture, we'd queue a task here.
        # For now, we return what's in the DB.
        
    cutoff = get_period_cutoff(period)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None
    
    return repo.load_history(ticker, from_date=cutoff_str)

# ── ETF Name Cache (Process-level LRU + SQLite backing) ──────────────────────

def get_etf_name(ticker: str) -> str | None:
    """
    Retrieve ETF name from assets table.
    Memory caching is handled by the caller (data_fetcher.py).
    """
    ticker = ticker.upper()
    conn = get_connection()
    try:
        row = conn.execute("SELECT name FROM assets WHERE ticker = ?", (ticker,)).fetchone()
        if row and row["name"]:
            return row["name"]
        return None
    finally:
        conn.close()

# ── Invalidation ─────────────────────────────────────────────────────────────

def invalidate_holding(ticker: str):
    """
    Clear all cached data for a ticker. Called on new transactions.
    """
    ticker = ticker.upper()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM market_prices WHERE ticker = ?", (ticker,))
        conn.execute("DELETE FROM price_history WHERE ticker = ?", (ticker,))
        conn.execute("DELETE FROM history_meta WHERE ticker = ?", (ticker,))
        conn.execute("DELETE FROM intraday_snapshots WHERE ticker = ?", (ticker,))
        conn.commit()
        logger.info(f"Invalidated cache for {ticker}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache for {ticker}: {e}")
    finally:
        conn.close()

def get_benchmarks_db() -> dict | None:
    """Read benchmark history from SQLite. Returns None if stale (> 1h) or empty."""
    import json
    import pandas as pd
    from data.database import get_connection
    conn = get_connection()
    try:
        # Check staleness of any entry (they are fetched together)
        row = conn.execute("SELECT history, fetched_at FROM benchmark_data LIMIT 1").fetchone()
        if not row:
            return None
            
        fetched_at = pd.to_datetime(row["fetched_at"])
        # History gating: 24h threshold for benchmarks
        if (pd.Timestamp.now() - fetched_at).total_seconds() > 86400:
            return None # Stale
            
        # If not stale, fetch all
        rows = conn.execute("SELECT label, history FROM benchmark_data").fetchall()
        return {r["label"]: json.loads(r["history"]) for r in rows}
    finally:
        conn.close()

def save_benchmarks_db(data: dict):
    """Save benchmark histories to SQLite."""
    import json
    from datetime import datetime
    from data.database import get_connection
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        for label, history in data.items():
            # Symbol mapping
            from services.market.data_fetcher import BENCHMARK_TICKERS
            symbol = next((k for k, v in BENCHMARK_TICKERS.items() if v == label), label)
            
            conn.execute('''
                INSERT OR REPLACE INTO benchmark_data (symbol, label, history, fetched_at)
                VALUES (?, ?, ?, ?)
            ''', (symbol, label, json.dumps(history), now))
        conn.commit()
    finally:
        conn.close()
