import os
import requests
import json
import logging
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from core import get_cache, set_cache
from core.engine.portfolio_engine import compute_tranche_pnl, compute_holding_pnl
from core.engine.utils import normalise_tz, get_period_cutoff
from config.settings import (
    API_MAX_RETRIES, API_RETRY_BACKOFF_BASE, CACHE_TTL_SECONDS,
    DATA_CACHE_DIR
)
from services.market.session_cache import (
    record_snapshot, get_session_history, clear_old_caches, backfill_session_cache
)
from services.market.market_status import (
    is_market_open, get_previous_trading_session_start
)

logger = logging.getLogger(__name__)

# Using market_prices table instead of snapshot file.
from data.database import get_connection
from data.cache_manager import save_live_prices, get_live_prices, get_etf_name as get_etf_name_db
from data.repository import PortfolioRepository, HistoryRepository

_NAME_CACHE: dict = {}
_NAME_CACHE_TTL = 86400

BENCHMARK_TICKERS = {
    "^GSPC": "S&P 500",
    "^AXJO": "ASX 200",
}
_BENCHMARK_CACHE_TTL = 3600

_INFO_CACHE: dict = {}
_INFO_CACHE_TTL = 3600  # Cache dividend/metadata for 1 hour


def get_ticker_cached(ticker_yf: str) -> yf.Ticker:
    """
    Returns a yfinance Ticker object.
    
    The intelligence_service uses this to fetch funds_data (sector/geo).
    While we avoid per-ticker price calls, funds_data is only available 
    via the Ticker object. Results are cached in intelligence_service.
    """
    return yf.Ticker(ticker_yf)


def get_etf_name(ticker: str) -> str:
    """
    Retrieve the long name for an ETF with multi-layer caching.
    Hierarchy: Memory Cache -> SQLite Assets Table -> yfinance API
    """
    from config.constants import NAMES
    
    ticker_upper = ticker.strip().upper()
    cache_key = f"name_{ticker_upper}"
    
    # 1. Check local memory cache (Hot)
    cached = _NAME_CACHE.get(cache_key)
    if cached and time.time() < cached[1]:
        return cached[0]
    
    # 2. Check SQLite Assets Table via cache_manager (Persistent)
    name = get_etf_name_db(ticker_upper)
    if name:
        _NAME_CACHE[cache_key] = (name, time.time() + _NAME_CACHE_TTL)
        return name

    fallback = NAMES.get(ticker_upper, ticker_upper)
    try:
        yf_ticker = f"{ticker_upper}.AX" if "." not in ticker_upper else ticker_upper
        
        # 3. Check info cache (Session)
        now = time.time()
        if yf_ticker in _INFO_CACHE:
            info, expiry = _INFO_CACHE[yf_ticker]
            if now < expiry:
                name = info.get("longName") or info.get("shortName") or fallback
                _NAME_CACHE[cache_key] = (name, now + _NAME_CACHE_TTL)
                # Persist to SQLite
                PortfolioRepository().upsert_asset(ticker_upper, name=name)
                return name

        # 4. Fetch from yfinance (Source)
        tk = get_ticker_cached(yf_ticker)
        raw_info = tk.info or {}
        
        # Memory Hygiene: Extract only what we need
        info = {
            "longName": raw_info.get("longName"),
            "shortName": raw_info.get("shortName"),
            "sector": raw_info.get("sector"),
            "country": raw_info.get("country"),
            "exDividendDate": raw_info.get("exDividendDate"),
            "dividendPayDate": raw_info.get("dividendPayDate")
        }
        
        # Update info cache
        _INFO_CACHE[yf_ticker] = (info, now + _INFO_CACHE_TTL)
        
        name = info.get("longName") or info.get("shortName") or fallback
        result = name.strip() if (isinstance(name, str) and len(name) > 3) else fallback
        
        # Update both caches
        _NAME_CACHE[cache_key] = (result, now + _NAME_CACHE_TTL)
        PortfolioRepository().upsert_asset(ticker_upper, name=result)
        
        return result
    except Exception as e:
        logger.warning("Name fetch failed for %s: %s", ticker_upper, e)
        return fallback


def save_portfolio_snapshot(data: dict) -> None:
    """Save the full portfolio state to the market_prices table."""
    if not data or "holdings" not in data:
        return
    save_live_prices(data["holdings"])

def load_portfolio_snapshot(initial_holdings: list[dict]) -> dict:
    """
    Load the portfolio state from the market_prices table and merge with
    the core holding data (shares/cost) built from transactions.
    """
    if not initial_holdings:
        return {"holdings": [], "fetched_at": datetime.now().strftime("%H:%M:%S")}

    tickers = [h["ticker"] for h in initial_holdings]
    db_prices = get_live_prices(tickers)
    
    enriched = []
    for h in initial_holdings:
        ticker = h["ticker"]
        p = db_prices.get(ticker, {})
        
        # Merge core (h) with enrichment (p)
        # Default to skeleton values for missing fields to prevent crashes
        # We ensure last_price and prev_close are NEVER None by falling back to avg_cost or 0
        merged = {
            **h,
            "last_price":     p.get("last_price") or h.get("avg_cost") or 0.0,
            "prev_close":     p.get("prev_close") or h.get("avg_cost") or 0.0,
            "day_high":       p.get("day_high") or h.get("avg_cost") or 0.0,
            "day_low":        p.get("day_low") or h.get("avg_cost") or 0.0,
            "day_chg":        p.get("day_chg") or 0.0,
            "day_chg_pct":    p.get("day_chg_pct") or 0.0,
            "day_pnl":        p.get("day_pnl") or 0.0,
            "mkt_value":      p.get("mkt_value") or h.get("total_cost") or 0.0,
            "pnl":            p.get("pnl") or 0.0,
            "pnl_pct":        p.get("pnl_pct") or 0.0,
            "annual_div":     p.get("annual_div") or 0.0,
            "realized_div":   p.get("realized_div") or 0.0,
            "div_yield":      p.get("div_yield") or 0.0,
            "div_frequency":  p.get("div_frequency") or "Unknown",
            "last_div_amount": p.get("last_div_amount") or 0.0,
            "last_div_date":  p.get("last_div_date"),
            "next_div_date":  p.get("next_div_date"),
            "payout_date":    p.get("payout_date"),
            "fetched_at":     p.get("fetched_at", "")
        }
        enriched.append(merged)
            
    fetched_at = "Unknown"
    if db_prices:
        first_p = next(iter(db_prices.values()))
        raw_fetched = first_p.get("fetched_at", "Unknown")
        if raw_fetched and raw_fetched != "Unknown":
            try:
                # Handle ISO format from DB
                if "T" in str(raw_fetched):
                    dt = datetime.fromisoformat(str(raw_fetched))
                    fetched_at = dt.strftime("%H:%M:%S")
                else:
                    fetched_at = str(raw_fetched)
            except:
                fetched_at = str(raw_fetched)[:8] # Fallback to start of string

    return {
        "holdings": enriched,
        "fetched_at": fetched_at
    }


def _download_with_retry(
    tickers: list[str],
    period: str,
    interval: str | None = None,
    actions: bool = False,
    max_retries: int = API_MAX_RETRIES,
    backoff_base: float = API_RETRY_BACKOFF_BASE
) -> pd.DataFrame:
    """
    Download market data using yfinance with retry logic.
    """
    for attempt in range(max_retries):
        try:
            kwargs = dict(
                period=period, group_by="ticker",
                auto_adjust=True, progress=False, actions=actions
            )
            if interval:
                kwargs["interval"] = interval
            df = yf.download(tickers, **kwargs)
            return df
        except Exception as e:
            error_str = str(e)
            is_401 = "401" in error_str
            
            if is_401:
                logger.warning("yfinance 401 Unauthorized (crumb expired). Resetting session...")
                try:
                    # Clear session cache if available, otherwise reset the session
                    if hasattr(yf.utils, "requests_cache"):
                        try:
                            yf.utils.requests_cache.clear()
                        except:
                            pass
                    
                    data_obj = yf.data.YfData()
                    if hasattr(data_obj, "_session"):
                        if data_obj._session:
                            try:
                                data_obj._session.close()
                            except:
                                pass
                        # Assign a fresh session; yfinance will handle crumb re-acquisition
                        data_obj._session = requests.Session()
                except Exception as reset_err:
                    logger.debug("Failed to reset yfinance session: %s", reset_err)

            if attempt == max_retries - 1:
                logger.warning("Download failed after %d attempts (period=%s): %s", max_retries, period, e)
                return pd.DataFrame()
            
            # Use 2s flat backoff for 401s, otherwise exponential
            sleep_time = 2.0 if is_401 else (backoff_base ** attempt)
            time.sleep(sleep_time)
    return pd.DataFrame()


def _extract_col(bulk_df: pd.DataFrame, ticker_yf: str, col_name: str) -> pd.Series:
    """Extract a column (Close, High, Low, Dividends, etc.) for a specific ticker from bulk download."""
    if bulk_df is None or bulk_df.empty:
        return pd.Series(dtype=float)
    cols = bulk_df.columns
    if not isinstance(cols, pd.MultiIndex):
        if col_name in cols:
            return bulk_df[col_name].dropna()
        # Fallback to similar names (yfinance can be inconsistent)
        for c in [col_name, col_name.replace(" ", ""), "Close", "Dividends"]:
            if c in cols:
                return bulk_df[c].dropna()
        # If it has standard columns, it is likely the ticker's data even if unnamed
        if 'Close' in cols or 'Open' in cols:
            if col_name in cols:
                return bulk_df[col_name].dropna()
        return pd.Series(dtype=float)

    # Try multiple combinations of MultiIndex keys
    candidates = [
        (ticker_yf, col_name),
        (col_name, ticker_yf),
        (ticker_yf.split(".")[0], col_name),
        (col_name, ticker_yf.split(".")[0])
    ]

    # Multi-index case
    for cand in candidates:
        if cand in cols:
            return bulk_df[cand].dropna()

    return pd.Series(dtype=float)


def extract_close(bulk_df: pd.DataFrame, ticker_yf: str) -> pd.Series:
    """
    Public API: extract the Close price series for a ticker from a bulk download DataFrame.
    Use this in services/ instead of importing the private _extract_col directly.
    """
    return _extract_col(bulk_df, ticker_yf, "Close")


def extract_dividends(bulk_df: pd.DataFrame, ticker_yf: str) -> pd.Series:
    """
    Public API: extract the Dividends series for a ticker from a bulk download DataFrame.
    """
    return _extract_col(bulk_df, ticker_yf, "Dividends")


def _extract_scalar(bulk_df: pd.DataFrame, ticker_yf: str, col_name: str) -> float:
    """
    Extract the last scalar value of a column for a ticker from a bulk download.
    Returns 0.0 if not found.
    """
    s = _extract_col(bulk_df, ticker_yf, col_name)
    if s.empty:
        return 0.0
    return float(s.iloc[-1])


def _compute_dividends_bulk(
    div_s: pd.Series,
    total_shares: float,
    mkt_value: float,
) -> tuple[float, float, float]:
    """
    Compute aggregate dividend metrics from a historical series.

    Args:
        div_s: Series of historical dividend payments per share.
        total_shares: Current number of shares held.
        mkt_value: Current total market value of the holding.

    Returns:
        tuple: (Annual Dividend $, Total Historical Dividend $, Dividend Yield %)
    """
    if div_s.empty:
        return 0.0, 0.0, 0.0

    div_s = div_s[div_s > 0]
    if div_s.empty:
        return 0.0, 0.0, 0.0

    div_s.index = normalise_tz(div_s.index)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)

    annual_per_share = float(div_s[div_s.index >= cutoff].sum())
    total_per_share  = float(div_s.sum())

    annual_div = round(annual_per_share * total_shares, 2)
    total_div  = round(total_per_share  * total_shares, 2)
    div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0.0, 2)

    return annual_div, total_div, div_yield


def _calculate_realized_dividends(div_s: pd.Series, tranches: list[dict]) -> float:
    """
    Calculate actual dividends received based on holding history.
    
    Logic:
      - Matches historical Ex-Dividend dates against shares held on those dates.
      - A tranche is eligible if the purchase date is strictly BEFORE the Ex-date.
      - This provides a "realized" figure rather than a generic annual yield.

    Args:
        div_s: Series of historical dividend payments per share.
        tranches: List of buy tranches for the ticker.

    Returns:
        float: Total dollar amount of dividends realized by the user.
    """
    if div_s.empty or not tranches:
        return 0.0

    div_s = div_s[div_s > 0]
    if div_s.empty:
        return 0.0

    # Ensure tz-naive for comparison
    div_s.index = normalise_tz(div_s.index)
    total_received = 0.0

    for ex_date, amount in div_s.items():
        # Ex-date determines eligibility. Most brokers use Ex-date + 1 business day 
        # or the settlement date, but for simplicity we check if purchase was BEFORE Ex-date.
        shares_on_date = sum(
            t["shares"] for t in tranches
            if pd.to_datetime(t["date"]).tz_localize(None) < ex_date
        )

        if shares_on_date > 0:
            total_received += shares_on_date * amount

    return round(total_received, 2)


def _deduce_frequency(div_s: pd.Series) -> str:
    """
    Deduce dividend frequency from historical distribution dates.
    """
    if div_s.empty:
        return "Unknown"

    div_s = div_s[div_s > 0]
    if len(div_s) < 2:
        # Check if the single distribution looks like an annual one
        return "Annual" if len(div_s) == 1 else "Unknown"

    dates = pd.to_datetime(div_s.index).sort_values()
    diffs = dates.to_series().diff().dt.days.dropna()
    median_diff = diffs.median()

    if 25 <= median_diff <= 35:
        return "Monthly"
    elif 80 <= median_diff <= 105:
        return "Quarterly"
    elif 170 <= median_diff <= 195:
        return "Semi-Annual"
    elif 350 <= median_diff <= 375:
        return "Annual"
    else:
        return "Irregular"


def fetch_benchmarks(period: str = "max") -> dict[str, list[dict]]:
    """
    Fetch S&P 500 (^GSPC) and ASX 200 (^AXJO) close series using bulk download.
    """
    cache_key = f"benchmarks_{period}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    result: dict[str, list[dict]] = {}
    symbols = list(BENCHMARK_TICKERS.keys())

    try:
        bulk_df = _download_with_retry(symbols, period=period)
        if bulk_df.empty:
            return {}

        for symbol, label in BENCHMARK_TICKERS.items():
            close = _extract_col(bulk_df, symbol, "Close")
            if close.empty:
                continue

            close.index = normalise_tz(pd.to_datetime(close.index))
            result[label] = [
                {"Date": d.strftime("%Y-%m-%d"), "Close": round(float(v), 4)}
                for d, v in close.items()
            ]
    except Exception as exc:
        logger.warning("Bulk benchmark fetch failed: %s", exc)

    if result:
        set_cache(cache_key, result, ttl=_BENCHMARK_CACHE_TTL)
    return result


def _enrich_single_holding(h: dict, multi_live: pd.DataFrame, multi_period: pd.DataFrame, hist_period: str) -> tuple[dict, list[dict] | None]:
    """
    Helper to enrich a single holding with market data, dividends, and P&L.
    Designed to run in a thread pool to parallelize I/O-bound metadata fetching.
    """
    ticker    = h["ticker"]
    ticker_yf = h["ticker_yf"]
    history_data = None
    
    # Ensure name is resolved (expensive I/O)
    if "name" not in h or h["name"] == ticker:
        h["name"] = get_etf_name(ticker)

    try:
        # 1. Chart history
        close_p = pd.Series(dtype=float)
        if hist_period == "1d":
            yf_1d = _extract_col(multi_period, ticker_yf, "Close")
            if not yf_1d.empty:
                yf_1d = yf_1d[yf_1d > 0]
                yf_1d.index = normalise_tz(yf_1d.index)
                
                # Allow data from the previous trading session (15:00 onwards)
                cutoff = get_previous_trading_session_start()
                cutoff_utc = normalise_tz(pd.DatetimeIndex([cutoff]))[0]
                yf_1d = yf_1d[yf_1d.index >= cutoff_utc]
            
            sess_1d = get_session_history(ticker)
            if not sess_1d.empty:
                sess_1d = sess_1d[sess_1d > 0]
                sess_1d.index = pd.to_datetime(sess_1d.index).tz_localize("Australia/Sydney")
                sess_1d.index = normalise_tz(sess_1d.index)
            
            if not yf_1d.empty and not sess_1d.empty:
                close_p = pd.concat([yf_1d, sess_1d]).sort_index()
                close_p = close_p[~close_p.index.duplicated(keep='last')]
            else:
                close_p = sess_1d if not sess_1d.empty else yf_1d
            
            if not close_p.empty:
                # Prepare history_data for export/backfill (must use Sydney time)
                # Note: close_p itself stays normalized (UTC) for P&L calculations
                exp_p = close_p.copy()
                # Ensure it's in Sydney time for the string representation
                try:
                    exp_p.index = pd.to_datetime(exp_p.index).tz_localize("UTC").tz_convert("Australia/Sydney")
                except Exception:
                    pass
                
                df_p = exp_p.reset_index()
                df_p.columns = ["Date", "Close"]
                # Format as string for JSON/dict serialization
                df_p["Date"] = df_p["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")
                history_data = df_p.to_dict("records")
        else:
            # ── 1b. OHLC Extraction (Extended History) ───────────────────
            # Extracts full candle data to support Candlestick charts.
            # We extract columns individually because bulk download 
            # might have missing values for specific tickers/periods.
            ohlc_cols = ["Open", "High", "Low", "Close"]
            dfs = []
            for col in ohlc_cols:
                s = _extract_col(multi_period, ticker_yf, col)
                if not s.empty:
                    s.name = col
                    dfs.append(s)
            
            if dfs:
                # Combine and drop rows where Close is missing (minimum requirement)
                df_combined = pd.concat(dfs, axis=1).dropna(subset=["Close"])
                if not df_combined.empty:
                    df_combined.index = normalise_tz(pd.to_datetime(df_combined.index))
                    history_data = df_combined.reset_index().to_dict("records")
                    close_p = df_combined["Close"]

        # 2. Market Metrics
        close_f = get_cache(f"close_series_{ticker_yf}")
        div_f   = get_cache(f"dividends_{ticker_yf}")
        
        if close_f is None or div_f is None:
            # Fallback for safety - should be rare if fetch_live is working correctly
            logger.debug(f"Cache miss for {ticker_yf} Close/Div in enrich loop")
            close_f = pd.Series(dtype=float)
            div_f = pd.Series(dtype=float)

        if not close_f.empty:
            close_f.index = normalise_tz(pd.to_datetime(close_f.index))

        live_close = _extract_col(multi_live, ticker_yf, "Close")
        live_high  = _extract_col(multi_live, ticker_yf, "High")
        live_low   = _extract_col(multi_live, ticker_yf, "Low")

        # 1. Determine Last Price and Previous Close (for daily P&L)
        last_price = h["avg_cost"]
        prev_close = h["avg_cost"]
        
        # Latest price from live feed
        if not live_close.empty:
            last_price = float(live_close.iloc[-1])
            if last_price == 0.0:
                # Fallback to previous interval if market is just opening with 0.0 bids
                last_price = float(live_close.iloc[-2]) if len(live_close) >= 2 else h["avg_cost"]
        elif not close_f.empty:
            last_price = float(close_f.iloc[-1])

        # Previous session close (CRITICAL for correct Day P&L)
        today_start = pd.Timestamp.now(tz="Australia/Sydney").normalize()
        # Find points strictly before today in the 5-day feed
        # Ensure live_close index is timezone-aware for comparison if it isn't already
        try:
            if live_close.index.tz is None:
                live_close.index = live_close.index.tz_localize("Australia/Sydney")
        except:
            pass
            
        yesterday_points = live_close[live_close.index < today_start]
        if not yesterday_points.empty:
            prev_close = float(yesterday_points.iloc[-1])
        elif len(close_f) >= 2:
            # Fallback to daily history: iloc[-1] is usually today, iloc[-2] is yesterday
            prev_close = float(close_f.iloc[-2])
        else:
            prev_close = last_price


        day_high = float(live_high.iloc[-1]) if not live_high.empty else last_price
        day_low  = float(live_low.iloc[-1])  if not live_low.empty  else last_price

        _pnl      = compute_holding_pnl(h, last_price, prev_close)
        mkt_value = _pnl["mkt_value"]

        annual_div, total_div, div_yield = _compute_dividends_bulk(div_f, h["total_shares"], mkt_value)
        realized_div = _calculate_realized_dividends(div_f, h.get("buy_tranches", []))
        div_frequency = _deduce_frequency(div_f)
        div_f_clean = div_f[div_f > 0]
        last_div_amount = float(div_f_clean.iloc[-1]) if not div_f_clean.empty else 0.0

        # Tranche P&L lists are no longer returned by default to save memory.
        # They should be computed lazily in the chart callbacks if needed.
        enriched_h = {
            **h,
            "last_price":     round(last_price, 3),
            "prev_close":     round(prev_close, 3),
            "day_high":       round(day_high, 3),
            "day_low":        round(day_low, 3),
            "mkt_value":      mkt_value,
            "pnl":            _pnl["pnl"],
            "pnl_pct":        _pnl["pnl_pct"],
            "day_pnl":        _pnl["day_pnl"],
            "day_chg":        _pnl["day_chg"],
            "day_chg_pct":    _pnl["day_chg_pct"],
            "total_div":      total_div,
            "realized_div":   realized_div,
            "annual_div":     annual_div,
            "div_yield":      div_yield,
            "div_frequency":  div_frequency,
            "last_div_amount": round(last_div_amount, 4),
            "last_div_date":   div_f.index[-1].strftime("%Y-%m-%d") if not div_f.empty else None,
            "tranches":       h.get("buy_tranches", []), # Keep base tranche data
        }
        
        # 3. Upcoming Dividends (expensive I/O - using TTL cache)
        try:
            now = time.time()
            if ticker_yf in _INFO_CACHE:
                info, expiry = _INFO_CACHE[ticker_yf]
                if now >= expiry:
                    tk = get_ticker_cached(ticker_yf)
                    raw_info = tk.info or {}
                    # Memory Hygiene: Extract only what we need to prevent 1GB+ bloat
                    info = {
                        "longName": raw_info.get("longName"),
                        "shortName": raw_info.get("shortName"),
                        "sector": raw_info.get("sector"),
                        "country": raw_info.get("country"),
                        "exDividendDate": raw_info.get("exDividendDate"),
                        "dividendPayDate": raw_info.get("dividendPayDate")
                    }
                    _INFO_CACHE[ticker_yf] = (info, now + _INFO_CACHE_TTL)
            else:
                tk = get_ticker_cached(ticker_yf)
                raw_info = tk.info or {}
                info = {
                    "longName": raw_info.get("longName"),
                    "shortName": raw_info.get("shortName"),
                    "sector": raw_info.get("sector"),
                    "country": raw_info.get("country"),
                    "exDividendDate": raw_info.get("exDividendDate"),
                    "dividendPayDate": raw_info.get("dividendPayDate")
                }
                _INFO_CACHE[ticker_yf] = (info, now + _INFO_CACHE_TTL)

            enriched_h["next_div_date"] = None
            enriched_h["payout_date"] = None
            
            ex_date = info.get("exDividendDate")
            pay_date = info.get("dividendPayDate")
            
            if ex_date:
                dt = datetime.fromtimestamp(ex_date) if isinstance(ex_date, int) else pd.to_datetime(ex_date)
                enriched_h["next_div_date"] = dt.strftime("%Y-%m-%d")
            if pay_date:
                dt = datetime.fromtimestamp(pay_date) if isinstance(pay_date, int) else pd.to_datetime(pay_date)
                enriched_h["payout_date"] = dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        return enriched_h, history_data

    except Exception as exc:
        logger.warning("Failed to enrich %s: %s", ticker_yf, exc)
        fallback_price = round(h["avg_cost"], 3)
        fallback_cost  = round(h["total_shares"] * h["avg_cost"], 2)
        return {
            **h,
            "last_price":  fallback_price, "prev_close":  fallback_price,
            "day_high":    fallback_price, "day_low":     fallback_price,
            "mkt_value":   fallback_cost, "pnl": 0.0, "pnl_pct": 0.0,
            "day_pnl": 0.0, "day_chg": 0.0, "day_chg_pct": 0.0,
            "total_div": 0.0, "realized_div": 0.0, "annual_div": 0.0, "div_yield": 0.0,
            "div_frequency": "Unknown", "last_div_amount": 0.0,
            "last_div_date": None, "next_div_date": None, "payout_date": None, "tranches": [],
        }, None


def get_full_history_cache(holdings: list[dict]) -> pd.DataFrame:
    """
    Helper to reconstruct a minimal DataFrame with 'Close' columns 
    from the compact server-side cache.
    Note: This is a reconstructed DataFrame, not the original bulk download.
    """
    if not holdings:
        return pd.DataFrame()
        
    series_dict = {}
    for h in holdings:
        ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
        s = get_cache(f"close_series_{ticker_yf}")
        if s is not None and not s.empty:
            # Reconstruct MultiIndex structure (Close, Ticker)
            series_dict[("Close", ticker_yf)] = s
            
    if not series_dict:
        return pd.DataFrame()
        
    df = pd.DataFrame(series_dict)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def fetch_portfolio_history(holdings: list[dict], period: str) -> dict:
    """
    Fetch history for all holdings in a portfolio concurrently.
    Returns a dict mapping ticker -> history list of dicts.
    """
    histories = {}
    if not holdings:
        return histories
        
    with ThreadPoolExecutor(max_workers=min(len(holdings), 10)) as executor:
        futures = {executor.submit(fetch_ticker_history, h["ticker"], period): h["ticker"] for h in holdings}
        for future in futures:
            ticker = futures[future]
            try:
                histories[ticker] = future.result()
            except Exception as e:
                logger.error(f"Batch fetch failed for {ticker}: {e}")
    return histories
    if not holdings:
        return pd.DataFrame()
        
    tickers_yf = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(sorted(tickers_yf))
    full_cache_key = f"bulk_full_{tickers_str.replace(' ', '_')}"
    
    cached = get_cache(full_cache_key)
    if cached is not None:
        return cached
    return pd.DataFrame()




def fetch_ticker_history(ticker: str, period: str) -> list[dict]:
    """
    Standalone lazy fetcher for ticker history.
    Checks SQLite cache first; fetches from yfinance if stale or missing.
    """
    repo = HistoryRepository()
    
    ticker_upper = ticker.upper()
    ticker_yf = f"{ticker_upper}.AX" if "." not in ticker_upper else ticker_upper
    
    # 1. Check if stale or missing (now depth-aware)
    if repo.is_stale(ticker_upper, requested_period=period):
        logger.info(f"History stale/missing for {ticker_upper} (period={period}). Fetching from yfinance.")
        try:
            # Normalize period for yfinance
            yf_period = period if period != "Since purchase" else "max"
            
            # Fetch slightly more than needed to ensure overlap/continuity
            df = _download_with_retry([ticker_yf], period=yf_period)
            if not df.empty:
                # Extract OHLC
                ohlc_cols = ["Open", "High", "Low", "Close", "Volume"]
                dfs = []
                for col in ohlc_cols:
                    s = _extract_col(df, ticker_yf, col)
                    if not s.empty:
                        s.name = col
                        dfs.append(s)
                
                if dfs:
                    df_combined = pd.concat(dfs, axis=1).dropna(subset=["Close"])
                    if not df_combined.empty:
                        df_combined.index = normalise_tz(pd.to_datetime(df_combined.index))
                        df_combined.index.name = "Date"
                        records = df_combined.reset_index().to_dict("records")
                        # Format Date as string for repository
                        for r in records:
                            r["Date"] = r["Date"].strftime("%Y-%m-%d %H:%M:%S")
                        
                        repo.save_history(ticker_upper, records, period=yf_period)
        except Exception as e:
            logger.error(f"Lazy fetch failed for {ticker_upper}: {e}")

    # 2. Return from SQLite
    from_date = get_period_cutoff(period)
    from_date_str = from_date.strftime("%Y-%m-%d") if from_date else None
        
    return repo.load_history(ticker_upper, from_date=from_date_str)


def fetch_live(holdings: list[dict], record_snapshots: bool = True) -> tuple[dict, dict, str]:
    """
    Fetch live prices, dividends and per-tranche P&L for all holdings.
    History is no longer fetched globally; use fetch_ticker_history() lazily.
    """
    if not holdings:
        return {}, {}, ""

    tickers_yf  = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(sorted(tickers_yf))
    
    # Outer cache key for the metrics (holdings, P&L)
    holdings_sig = "_".join(
        f"{h['ticker']}{h['total_shares']:.4f}" 
        for h in sorted(holdings, key=lambda x: x['ticker'])
    )
    cache_key = f"market_data_v3_{holdings_sig}"
    # Cache check: Skip cache if we are recording snapshots (Worker context)
    # This ensures the worker ALWAYS fetches fresh data from yfinance.
    cached = get_cache(cache_key) if not record_snapshots else None
    
    if cached:
        if record_snapshots:
            try:
                record_snapshot(cached["holdings"])
            except Exception as e:
                logger.error("Cached snapshot recording failed: %s", e)

        res = cached.copy()
        res["fetched_at"] = datetime.now().strftime("%H:%M:%S")
        return res, {}, holdings_sig

    # ── A. Live quotes: single bulk 5-day download ────────────────────────────
    logger.info("Fetching live quotes (5d) for %d tickers", len(tickers_yf))
    multi_live = _download_with_retry(tickers_yf, period="5d", interval="5m")

    # ── A2. Backfill Session Cache ────────────────────────────────────────────
    # Use the 5-day data to fill any gaps in today's intraday history
    try:
        backfill_map = {}
        for t_yf in tickers_yf:
            ticker_short = t_yf.split(".")[0]
            s = extract_close(multi_live, t_yf)
            if not s.empty:
                backfill_map[ticker_short] = s
        
        if backfill_map:
            # Backfill from 15:00 previous trading day to ensure continuity
            start_limit = get_previous_trading_session_start()
            backfill_session_cache(backfill_map, start_limit=start_limit)
    except Exception as e:
        logger.error("Backfill failed in fetch_live: %s", e)


    # ── B. Full history: extracted to compact series ──────────────────────────
    # Optimization: Only fetch history for tickers missing from cache.
    missing_history = [t for t in tickers_yf if get_cache(f"close_series_{t}") is None or get_cache(f"dividends_{t}") is None]
    
    if missing_history:
        logger.info("Fetching full history (max) for %d missing tickers", len(missing_history))
        multi_full = _download_with_retry(missing_history, period="max", actions=True)
        if not multi_full.empty:
            for t_yf in missing_history:
                close_s = extract_close(multi_full, t_yf)
                div_s = extract_dividends(multi_full, t_yf)
                
                # Cache compact Series
                if not close_s.empty:
                    # 24h cache for technicals to prevent redundant history churn
                    set_cache(f"close_series_{t_yf}", close_s, ttl=86400)
                if not div_s.empty:
                    # Filter for non-zero dividends to save even more space
                    div_s = div_s[div_s > 0]
                    # 7d cache for dividends as they change rarely
                    set_cache(f"dividends_{t_yf}", div_s, ttl=604800)
            
            # Explicitly clear multi_full reference to free RAM before enrichment starts
            del multi_full

    # ── C. Enrichment ─────────────────────────────────────────────────────────
    enriched: list[dict] = []
    
    # Side Effect: Persist 5-day live OHLC to SQLite
    repo = HistoryRepository()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Pass multi_live as the period data for enrichment when period="1d" (dummy here)
        futures = [
            executor.submit(_enrich_single_holding, h, multi_live, pd.DataFrame(), "max")
            for h in holdings
        ]
        results = [f.result() for f in futures]
    
    for h_enriched, _ in results:
        enriched.append(h_enriched)
        
        # Save live OHLC records as a side effect
        try:
            ticker_yf = h_enriched["ticker_yf"]
            ticker_short = h_enriched["ticker"]
            
            # Extract OHLC for this ticker from multi_live
            ohlc_cols = ["Open", "High", "Low", "Close", "Volume"]
            ticker_dfs = []
            for col in ohlc_cols:
                s = _extract_col(multi_live, ticker_yf, col)
                if not s.empty:
                    s.name = col
                    ticker_dfs.append(s)
            
            if ticker_dfs:
                df_ticker = pd.concat(ticker_dfs, axis=1).dropna(subset=["Close"])
                if not df_ticker.empty:
                    # Convert index (Timestamp) to string for HistoryRepository
                    df_ticker.index = pd.to_datetime(df_ticker.index)
                    df_ticker.index.name = "Date"
                    records = df_ticker.reset_index().to_dict("records")
                    for r in records:
                        if isinstance(r["Date"], pd.Timestamp):
                            r["Date"] = r["Date"].strftime("%Y-%m-%d %H:%M:%S")
                    # Save to SQLite
                    repo.save_history(ticker_short, records, period="5d")
        except Exception as e:
            logger.error(f"Failed to save live side-effect history for {h_enriched['ticker']}: {e}")

    result = {
        "holdings":   enriched,
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
    }
    
    # ── Record snapshot for P&L tracking ──────────────────────────────────────
    if record_snapshots:
        try:
            record_snapshot(enriched)
        except Exception as PERSIST_EXC:
            logger.error("Snapshot recording failed: %s", PERSIST_EXC)
    
    clear_old_caches()
    set_cache(cache_key, result, ttl=CACHE_TTL_SECONDS)
    
    # ── Save snapshot for fast startup ───────────────────────────────────────
    if result.get("holdings"):
        save_portfolio_snapshot(result)
        
    logger.info("Done — %d enriched (no global history)", len(enriched))
    return result, {}, holdings_sig
