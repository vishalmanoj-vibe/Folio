import os
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

SNAPSHOT_PATH = os.path.join(DATA_CACHE_DIR, "portfolio_snapshot.json")

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
    from data.repository import PortfolioRepository
    
    ticker_upper = ticker.strip().upper()
    cache_key = f"name_{ticker_upper}"
    
    # 1. Check local memory cache (Hot)
    cached = _NAME_CACHE.get(cache_key)
    if cached and time.time() < cached[1]:
        return cached[0]
    
    # 2. Check SQLite Assets Table (Persistent)
    repo = PortfolioRepository()
    asset = repo.get_asset(ticker_upper)
    if asset and asset.get("name"):
        name = asset["name"]
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
                repo.upsert_asset(ticker_upper, name=name)
                return name

        # 4. Fetch from yfinance (Source)
        tk = get_ticker_cached(yf_ticker)
        info = tk.info or {}
        
        # Update info cache
        _INFO_CACHE[yf_ticker] = (info, now + _INFO_CACHE_TTL)
        
        name = info.get("longName") or info.get("shortName") or fallback
        result = name.strip() if (isinstance(name, str) and len(name) > 3) else fallback
        
        # Update both caches
        _NAME_CACHE[cache_key] = (result, now + _NAME_CACHE_TTL)
        repo.upsert_asset(ticker_upper, name=result)
        
        return result
    except Exception as e:
        logger.warning("Name fetch failed for %s: %s", ticker_upper, e)
        return fallback


def save_portfolio_snapshot(data: dict) -> None:
    """Save the full portfolio state to a disk snapshot for fast startup."""
    if not data or "holdings" not in data:
        return
        
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(data, f, default=str)
        logger.info("Portfolio snapshot saved to disk")
    except Exception as e:
        logger.error("Failed to save portfolio snapshot: %s", e)


def load_portfolio_snapshot() -> dict | None:
    """Load the portfolio state from a disk snapshot."""
    if not os.path.exists(SNAPSHOT_PATH):
        return None
        
    try:
        with open(SNAPSHOT_PATH, "r") as f:
            data = json.load(f)
        logger.info("Portfolio snapshot loaded from disk")
        return data
    except Exception as e:
        logger.error("Failed to load portfolio snapshot: %s", e)
        return None


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
            if attempt == max_retries - 1:
                logger.warning("Download failed after %d attempts (period=%s): %s", max_retries, period, e)
                return pd.DataFrame()
            time.sleep(backoff_base ** attempt)
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


def _enrich_single_holding(h: dict, multi_live: pd.DataFrame, multi_full: pd.DataFrame, multi_period: pd.DataFrame, hist_period: str) -> tuple[dict, list[dict] | None]:
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
        close_f = _extract_col(multi_full, ticker_yf, "Close")
        div_f   = _extract_col(multi_full, ticker_yf, "Dividends")
        if not close_f.empty:
            close_f.index = normalise_tz(pd.to_datetime(close_f.index))

        live_close = _extract_col(multi_live, ticker_yf, "Close")
        live_high  = _extract_col(multi_live, ticker_yf, "High")
        live_low   = _extract_col(multi_live, ticker_yf, "Low")

        if len(live_close) >= 2:
            last_price = float(live_close.iloc[-1])
            prev_close = float(live_close.iloc[-2])
            # FIX: zero-price fallback for ASX off-hours
            if last_price == 0.0 or last_price is None:
                last_price = prev_close if prev_close else h["avg_cost"]
        elif len(live_close) == 1:
            last_price = float(live_close.iloc[-1])
            prev_close = float(close_f.iloc[-2]) if len(close_f) >= 2 else last_price
            # FIX: zero-price fallback for ASX off-hours
            if last_price == 0.0 or last_price is None:
                last_price = prev_close if prev_close else h["avg_cost"]
        else:
            last_price = float(close_f.iloc[-1]) if len(close_f) >= 1 else h["avg_cost"]
            prev_close = float(close_f.iloc[-2]) if len(close_f) >= 2 else last_price
            # FIX: zero-price fallback for ASX off-hours
            if last_price == 0.0 or last_price is None:
                last_price = prev_close if prev_close else h["avg_cost"]

        day_high = float(live_high.iloc[-1]) if not live_high.empty else last_price
        day_low  = float(live_low.iloc[-1])  if not live_low.empty  else last_price

        _pnl      = compute_holding_pnl(h, last_price, prev_close)
        mkt_value = _pnl["mkt_value"]

        annual_div, total_div, div_yield = _compute_dividends_bulk(div_f, h["total_shares"], mkt_value)
        realized_div = _calculate_realized_dividends(div_f, h.get("buy_tranches", []))
        div_frequency = _deduce_frequency(div_f)
        div_f_clean = div_f[div_f > 0]
        last_div_amount = float(div_f_clean.iloc[-1]) if not div_f_clean.empty else 0.0

        tranche_data = []
        if not close_p.empty:
            tranche_data = compute_tranche_pnl(close_p, h.get("buy_tranches", []))
        elif not close_f.empty and hist_period != "1d":
            tranche_data = compute_tranche_pnl(close_f, h.get("buy_tranches", []))

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
            "tranches":       tranche_data,
        }
        
        # 3. Upcoming Dividends (expensive I/O - using TTL cache)
        try:
            now = time.time()
            if ticker_yf in _INFO_CACHE:
                info, expiry = _INFO_CACHE[ticker_yf]
                if now >= expiry:
                    tk = get_ticker_cached(ticker_yf)
                    info = tk.info or {}
                    _INFO_CACHE[ticker_yf] = (info, now + _INFO_CACHE_TTL)
            else:
                tk = get_ticker_cached(ticker_yf)
                info = tk.info or {}
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
    Helper to reconstruct the exact cache key for the full OHLC history
    and retrieve it from the server-side cache.
    """
    if not holdings:
        return pd.DataFrame()
        
    tickers_yf = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(sorted(tickers_yf))
    full_cache_key = f"bulk_full_{tickers_str.replace(' ', '_')}"
    
    cached = get_cache(full_cache_key)
    if cached is not None:
        return cached
    return pd.DataFrame()


def fetch_live(holdings: list[dict], hist_period: str = "max", record_snapshots: bool = True, use_disk_history: bool = False) -> dict:
    """
    Fetch live prices, history, dividends and per-tranche P&L for all holdings.

    Live price strategy (no fast_info):
    ─────────────────────────────────────
    fast_info.last_price internally calls tk.history(period="1y") making it
    slow and unreliable. Instead we do a single bulk yf.download(period="1d")
    for all tickers which returns today's Open/High/Low/Close and yesterday's
    Close (as the previous row) — cheap, accurate, and one network call.
    """
    if not holdings:
        return {}

    tickers_yf  = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(sorted(tickers_yf))

    # Normalize period string (yfinance is case-sensitive, prefers lowercase)
    hist_period = hist_period.lower()
    
    # Outer cache key includes tickers so adding/removing a holding busts it
    holdings_sig = "_".join(
        f"{h['ticker']}{h['total_shares']:.4f}" 
        for h in sorted(holdings, key=lambda x: x['ticker'])
    )
    # FIX: include share counts in cache key to bust on new transactions
    cache_key = f"market_data_v2_{hist_period}_{holdings_sig}"
    cached = get_cache(cache_key)
    if cached:
        # ── Record snapshots even on cache hits for continuity ────────────────
        if record_snapshots:
            try:
                record_snapshot(cached["holdings"])
                if hist_period == "1d":
                    backfill_map = {}
                    for ticker, hist_list in cached.get("histories", {}).items():
                        if hist_list:
                            df_h = pd.DataFrame(hist_list)
                            if not df_h.empty and "Date" in df_h.columns and "Close" in df_h.columns:
                                backfill_map[ticker] = df_h.set_index("Date")["Close"]
                    if backfill_map:
                        start_limit = get_previous_trading_session_start()
                        backfill_session_cache(backfill_map, start_limit=start_limit)
            except Exception as e:
                logger.error("Cached snapshot recording failed: %s", e)

        # Return a copy with fresh timestamp so Dash detects the change
        res = cached.copy()
        res["fetched_at"] = datetime.now().strftime("%H:%M:%S")
        return res

    # ── A. Live quotes: single bulk 5-day download ────────────────────────────
    # Strategy:
    # Instead of slow per-ticker calls, we download the last 5 days for ALL tickers.
    # - iloc[-1] = Today's current price (or most recent close).
    # - iloc[-2] = Yesterday's close (prev_session).
    # This ensures accuracy even during ASX off-hours and is significantly faster 
    # than individual 'fast_info' calls which trigger separate network requests.
    logger.info("Fetching live quotes (5d) for %d tickers", len(tickers_yf))
    multi_live = _download_with_retry(tickers_yf, period="5d")

    # ── B. Full history: cached 1 hour — used for dividends + tranche P&L ────
    full_cache_key = f"bulk_full_{tickers_str.replace(' ', '_')}"
    multi_full = get_cache(full_cache_key)
    if multi_full is None:
        logger.info("Fetching full history (max) for %d tickers", len(tickers_yf))
        multi_full = _download_with_retry(tickers_yf, period="max", actions=True)
        if not multi_full.empty:
            set_cache(full_cache_key, multi_full, ttl=3600)

    # ── C. Chart history: the user-selected period ────────────────────────────
    if hist_period == "max" and not multi_full.empty:
        # Reuse multi_full if possible to save a redundant network call
        multi_period = multi_full
    elif hist_period == "1d":
        # Request 2d to include the final hour of the previous trading day
        multi_period = _download_with_retry(tickers_yf, period="2d", interval="5m")
    else:
        if use_disk_history:
            multi_period = pd.DataFrame()
        else:
            multi_period = _download_with_retry(tickers_yf, period=hist_period)

    enriched:  list[dict] = []
    histories: dict       = {}

    # Parallelize the enrichment process (I/O bound due to get_etf_name and tk.info)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_enrich_single_holding, h, multi_live, multi_full, multi_period, hist_period)
            for h in holdings
        ]
        results = [f.result() for f in futures]
    
    if use_disk_history:
        from data.watchlist_repository import WatchlistRepository
        repo = WatchlistRepository()
        today_str = datetime.now().strftime("%Y-%m-%d")
        for i, (h_enriched, _) in enumerate(results):
            ticker = h_enriched["ticker"]
            disk_history = repo.load_history(ticker)
            
            if not disk_history:
                repo.fetch_and_save_history(ticker)
                disk_history = repo.load_history(ticker)
                
            last_price = h_enriched.get("last_price")
            
            if disk_history and last_price:
                last_entry_date = disk_history[-1]["Date"]
                if last_entry_date != today_str:
                    disk_history.append({"Date": today_str, "Close": last_price})
                    repo.save_history(ticker, disk_history)
                else:
                    disk_history[-1]["Close"] = last_price
                    repo.save_history(ticker, disk_history)
            
            results[i] = (h_enriched, disk_history)
    
    for h_enriched, history_data in results:
        enriched.append(h_enriched)
        if history_data:
            histories[h_enriched["ticker"]] = history_data

    result = {
        "holdings":   enriched,
        "histories":  histories,
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
    }
    
    # ── Record snapshots for 'Today' chart persistence ───────────────────────
    if record_snapshots:
        try:
            # Always record the latest point for immediate continuity
            record_snapshot(enriched)
            
            # Additionally backfill if we have intraday history for the 'Today' chart
            if hist_period == "1d":
                backfill_map = {}
                for ticker, hist_list in histories.items():
                    if hist_list:
                        df_h = pd.DataFrame(hist_list)
                        if not df_h.empty and "Date" in df_h.columns and "Close" in df_h.columns:
                            backfill_map[ticker] = df_h.set_index("Date")["Close"]
                
                if backfill_map:
                    # Capture from the last hour of the previous trading day
                    start_limit = get_previous_trading_session_start()
                    backfill_session_cache(backfill_map, start_limit=start_limit)
        except Exception as PERSIST_EXC:
            logger.error("Snapshot/Backfill recording failed: %s", PERSIST_EXC)
    
    clear_old_caches()

    ttl = 5 if hist_period == "1d" else 10
    set_cache(cache_key, result, ttl=ttl)
    
    # ── Save snapshot for fast startup ───────────────────────────────────────
    if hist_period == "max" and result.get("holdings"):
        save_portfolio_snapshot(result)
        
    logger.info("Done — %d enriched, %d with history", len(enriched), len(histories))
    return result