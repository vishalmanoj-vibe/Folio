"""
services/market/fetcher.py
===========================
Market data fetching service.

Dividend fix (this version)
---------------------------
Previously tk.history(auto_adjust=False) returned a tz-aware DatetimeIndex.
Comparing it to a tz-naive cutoff string silently returned no rows, so every
holding accumulated all-time dividends and yields were wildly wrong (e.g. SEMI
showing 4.5%).

Fix:
  1. Use auto_adjust=True (default) — split-adjusted per-share dividends.
  2. Strip timezone from the dividend index via tz_convert(None) before the
     cutoff comparison.

Benchmark fetch (this version)
-------------------------------
fetch_benchmarks() downloads ^GSPC (S&P 500) and ^AXJO (ASX 200) and returns
JSON-serialisable records.  Cached 1 h independently of portfolio data.
"""

import logging
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from core import get_cache, set_cache
from core.engine.portfolio_engine import compute_tranche_pnl, compute_holding_pnl
from config.settings import API_MAX_RETRIES, API_RETRY_BACKOFF_BASE, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

_NAME_CACHE: dict = {}
_NAME_CACHE_TTL = 86400

BENCHMARK_TICKERS = {
    "^GSPC": "S&P 500",
    "^AXJO": "ASX 200",
}
_BENCHMARK_CACHE_TTL = 3600


def get_etf_name(ticker: str) -> str:
    """
    Retrieve the long name for an ETF from a dictionary of known names.

    Args:
        ticker: The ETF ticker symbol.

    Returns:
        The ETF name or a default string if not found.
    """
    from config.constants import NAMES
    ticker_upper = ticker.strip().upper()
    cache_key = f"name_{ticker_upper}"
    cached = _NAME_CACHE.get(cache_key)
    if cached and time.time() < cached[1]:
        return cached[0]
    fallback = NAMES.get(ticker_upper, ticker_upper)
    try:
        yf_ticker = f"{ticker_upper}.AX" if "." not in ticker_upper else ticker_upper
        tk = yf.Ticker(yf_ticker)
        try:
            if hasattr(tk, "funds_data") and tk.funds_data is not None:
                name = tk.funds_data.name
                if name and isinstance(name, str) and len(name) > 3:
                    result = name.strip()
                    _NAME_CACHE[cache_key] = (result, time.time() + _NAME_CACHE_TTL)
                    return result
        except Exception:
            pass
        info = tk.info or {}
        name = info.get("longName") or info.get("shortName") or ""
        result = name.strip() if (name and len(name) > 3 and name != ticker_upper) else fallback
        _NAME_CACHE[cache_key] = (result, time.time() + _NAME_CACHE_TTL)
        return result
    except Exception as e:
        logger.warning("Name fetch failed for %s: %s", ticker_upper, e)
        _NAME_CACHE[cache_key] = (fallback, time.time() + 3600)
        return fallback


def _download_with_retry(
    tickers: list[str], period: str, max_retries: int = API_MAX_RETRIES, backoff_base: float = API_RETRY_BACKOFF_BASE
) -> pd.DataFrame:
    """
    Download market data using yfinance with retry logic.

    Args:
        tickers: List of ticker symbols to fetch.
        period: Time period to fetch (e.g., '1mo', 'max').
        max_retries: Number of times to retry on failure.
        backoff_base: Base for exponential backoff.

    Returns:
        A pandas DataFrame of the fetched data.
    """
    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers, period=period, group_by="ticker",
                auto_adjust=False, progress=False,
            )
            return df
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning("Download failed after %d attempts (period=%s): %s", max_retries, period, e)
                return pd.DataFrame()
            time.sleep(backoff_base ** attempt)
    return pd.DataFrame()


def _extract_close(bulk_df: pd.DataFrame, ticker_yf: str) -> pd.Series:
    """
    Extract the adjusted close price for a specific ticker from the bulk DataFrame.

    Args:
        bulk_df: The DataFrame returned by yfinance download.
        ticker_yf: The ticker symbol to extract.

    Returns:
        A pandas Series of the adjusted close prices, sorted by date.
    """
    if bulk_df is None or bulk_df.empty:
        return pd.Series(dtype=float)
    cols = bulk_df.columns
    if not isinstance(cols, pd.MultiIndex):
        return bulk_df["Close"].dropna() if "Close" in cols else pd.Series(dtype=float)
    if (ticker_yf, "Close") in cols:
        return bulk_df[(ticker_yf, "Close")].dropna()
    if ("Close", ticker_yf) in cols:
        return bulk_df[("Close", ticker_yf)].dropna()
    base = ticker_yf.split(".")[0]
    if (base, "Close") in cols:
        return bulk_df[(base, "Close")].dropna()
    if ("Close", base) in cols:
        return bulk_df[("Close", base)].dropna()
    logger.warning("No Close column for %s", ticker_yf)
    return pd.Series(dtype=float)


def _normalise_tz(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Strip timezone from a DatetimeIndex so comparisons with tz-naive values work."""
    if index.tz is not None:
        return index.tz_convert("UTC").tz_localize(None)
    return index


def _compute_dividends(
    tk: "yf.Ticker",
    total_shares: float,
    mkt_value: float,
) -> tuple[float, float, float]:
    """
    Return (annual_div, total_div, div_yield) for a holding.

    Uses auto_adjust=True so dividends are already split-adjusted.
    Normalises the DatetimeIndex to tz-naive before the 365-day cutoff filter
    so the comparison actually works (previous bug: all-time dividends were
    accumulated because the tz-aware index comparison silently returned all rows).
    """
    try:
        hist_raw = tk.history(period="max", auto_adjust=True)
        if hist_raw.empty or "Dividends" not in hist_raw.columns:
            return 0.0, 0.0, 0.0

        div_s = hist_raw["Dividends"]
        div_s = div_s[div_s > 0]
        if div_s.empty:
            return 0.0, 0.0, 0.0

        # KEY FIX: strip timezone so >= comparison with tz-naive cutoff works
        div_s.index = _normalise_tz(div_s.index)

        cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
        annual_per_share = float(div_s[div_s.index >= cutoff].sum())
        total_per_share  = float(div_s.sum())

        annual_div = round(annual_per_share * total_shares, 2)
        total_div  = round(total_per_share  * total_shares, 2)
        div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0.0, 2)

        logger.debug(
            "Dividends: annual_per_share=%.4f  total=%.4f  shares=%.2f"
            "  annual_div=%.2f  yield=%.2f%%",
            annual_per_share, total_per_share, total_shares, annual_div, div_yield,
        )
        return annual_div, total_div, div_yield

    except Exception as exc:
        logger.warning("Dividend fetch failed: %s", exc)
        return 0.0, 0.0, 0.0


def fetch_benchmarks(period: str = "max") -> dict[str, list[dict]]:
    """
    Fetch S&P 500 (^GSPC) and ASX 200 (^AXJO) close series.

    Returns {"S&P 500": [{"Date": "YYYY-MM-DD", "Close": float}, ...], "ASX 200": [...]}
    Cached 1 h per period.  The chart callback slices to the display window.
    """
    cache_key = f"benchmarks_{period}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    result: dict[str, list[dict]] = {}

    for symbol, label in BENCHMARK_TICKERS.items():
        try:
            df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
            if df.empty:
                logger.warning("Benchmark %s empty for period=%s", symbol, period)
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if "Close" not in df.columns:
                logger.warning("No Close column for benchmark %s", symbol)
                continue

            close = df["Close"].dropna()
            close.index = pd.to_datetime(close.index)
            if close.index.tz is not None:
                close.index = close.index.tz_convert(None)

            result[label] = [
                {"Date": d.strftime("%Y-%m-%d"), "Close": round(float(v), 4)}
                for d, v in close.items()
            ]
            logger.info("Benchmark %s (%s): %d rows fetched", label, symbol, len(result[label]))

        except Exception as exc:
            logger.warning("Benchmark fetch failed for %s: %s", symbol, exc)

    set_cache(cache_key, result, ttl=_BENCHMARK_CACHE_TTL)
    return result


def fetch_live(holdings: list[dict], hist_period: str = "3mo") -> dict:
    """
    Fetch live prices, history, dividends and per-tranche P&L for all holdings.
    """
    if not holdings:
        return {}

    cache_key = f"market_data_{hist_period}"
    cached = get_cache(cache_key)
    if cached:
        logger.debug("Cache hit for period=%s", hist_period)
        return cached

    tickers_yf  = [h["ticker_yf"] for h in holdings]
    tickers_str = " ".join(tickers_yf)
    logger.info("Fetching %s  period=%s", tickers_yf, hist_period)

    multi_period = _download_with_retry(tickers_str, period=hist_period)
    multi_full   = _download_with_retry(tickers_str, period="max")

    enriched:  list[dict] = []
    histories: dict       = {}

    for h in holdings:
        ticker    = h["ticker"]
        ticker_yf = h["ticker_yf"]
        try:
            close_period = _extract_close(multi_period, ticker_yf)
            close_full   = _extract_close(multi_full,   ticker_yf)

            if not close_period.empty:
                close_period.index = pd.to_datetime(close_period.index).tz_localize(None)
            if not close_full.empty:
                close_full.index = pd.to_datetime(close_full.index).tz_localize(None)

            if not close_period.empty:
                df_p = close_period.reset_index()
                df_p.columns = ["Date", "Close"]
                histories[ticker] = df_p.to_dict("records")

            tk = yf.Ticker(ticker_yf)
            fi = tk.fast_info

            fi_last = fi.get("last_price")     or 0.0
            fi_prev = fi.get("previous_close") or 0.0
            fi_high = fi.get("day_high")       or 0.0
            fi_low  = fi.get("day_low")        or 0.0

            hist_last = float(close_full.iloc[-1]) if len(close_full) >= 1 else None
            hist_prev = float(close_full.iloc[-2]) if len(close_full) >= 2 else None

            last_price = float(fi_last if fi_last > 0 else (hist_last or h["avg_cost"]))
            prev_close = float(fi_prev if fi_prev > 0 else (hist_prev or last_price))
            day_high   = float(fi_high if fi_high > 0 else last_price)
            day_low    = float(fi_low  if fi_low  > 0 else last_price)

            logger.info(
                "%-6s  fi_last=%6.3f  hist_last=%s  hist_prev=%s  using=%.3f/%.3f",
                ticker, fi_last,
                f"{hist_last:.3f}" if hist_last else "N/A",
                f"{hist_prev:.3f}" if hist_prev else "N/A",
                last_price, prev_close,
            )

            _pnl        = compute_holding_pnl(h, last_price, prev_close)
            mkt_value   = _pnl["mkt_value"]
            pnl         = _pnl["pnl"]
            pnl_pct     = _pnl["pnl_pct"]
            day_chg     = _pnl["day_chg"]
            day_chg_pct = _pnl["day_chg_pct"]
            day_pnl     = _pnl["day_pnl"]

            # ── Dividends — tz-fixed ──────────────────────────────────────────
            annual_div, total_div, div_yield = _compute_dividends(
                tk, h["total_shares"], mkt_value
            )

            tranche_data: list[dict] = []
            if not close_full.empty:
                tranche_data = compute_tranche_pnl(close_full, h.get("buy_tranches", []))
            else:
                logger.warning("%s: close_full empty — no P&L tranche data", ticker)

            logger.info(
                "%-6s  pnl=%+.2f (%+.2f%%)  day=%+.2f  annual_div=%.2f  yield=%.2f%%",
                ticker, pnl, pnl_pct, day_pnl, annual_div, div_yield,
            )

            enriched.append({
                **h,
                "last_price":  round(last_price, 3),
                "prev_close":  round(prev_close, 3),
                "day_high":    round(day_high,   3),
                "day_low":     round(day_low,    3),
                "day_chg":     day_chg,
                "day_chg_pct": day_chg_pct,
                "day_pnl":     day_pnl,
                "mkt_value":   mkt_value,
                "pnl":         pnl,
                "pnl_pct":     pnl_pct,
                "total_div":   total_div,
                "annual_div":  annual_div,
                "div_yield":   div_yield,
                "tranches":    tranche_data,
            })

        except Exception as exc:
            logger.warning("Failed to enrich %s: %s — cost fallback", ticker_yf, exc)
            enriched.append({
                **h,
                "last_price": h["avg_cost"], "prev_close": h["avg_cost"],
                "day_high":   h["avg_cost"], "day_low":    h["avg_cost"],
                "day_chg": 0, "day_chg_pct": 0, "day_pnl": 0,
                "mkt_value": round(h["total_shares"] * h["avg_cost"], 2),
                "pnl": 0, "pnl_pct": 0,
                "total_div": 0, "annual_div": 0, "div_yield": 0,
                "tranches": [],
            })

    result = {
        "holdings":   enriched,
        "histories":  histories,
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
    }
    set_cache(cache_key, result, ttl=CACHE_TTL_SECONDS)
    logger.info("Done — %d enriched, %d with history", len(enriched), len(histories))
    return result