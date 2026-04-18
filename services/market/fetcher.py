"""
services/market/fetcher.py
===========================
Market data fetching service.

Fetches live prices, history, dividends, and P&L from yfinance.
Includes retry logic and caching.

Computation changes
-------------------
Two previously inline computation blocks are now delegated to the engine:

  • compute_holding_pnl()  — replaces the six manual day/pnl lines
  • compute_tranche_pnl()  — replaces the per-tranche for-loop

Everything else (yfinance calls, dividend logic, caching) is unchanged.
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

# ── ETF name cache ─────────────────────────────────────────────────────────────
_NAME_CACHE: dict = {}
_NAME_CACHE_TTL = 86400  # 24 hours


def get_etf_name(ticker: str) -> str:
    """
    Automatically fetch the clean, official name for any ETF.
    Priority order:
      1. funds_data (most reliable for ASX ETFs like CLNE, XMET)
      2. ticker.info longName / shortName
      3. Static fallback in config.constants.NAMES
      4. Ticker itself
    Cached 24 h.
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

        # Best source for ASX ETFs: funds_data
        try:
            if hasattr(tk, "funds_data") and tk.funds_data is not None:
                name = tk.funds_data.name
                if name and isinstance(name, str) and len(name) > 3:
                    result = name.strip()
                    _NAME_CACHE[cache_key] = (result, time.time() + _NAME_CACHE_TTL)
                    logger.debug("Got name from funds_data for %s: %s", ticker_upper, result)
                    return result
        except Exception:
            pass

        # Fallback to standard .info
        info = tk.info or {}
        name = (
            info.get("longName")
            or info.get("shortName")
            or info.get("quoteType", "").replace("ETF", "ETF").strip()
        )

        if name and isinstance(name, str) and len(name) > 3 and name != ticker_upper:
            result = name.strip()
        else:
            result = fallback

        _NAME_CACHE[cache_key] = (result, time.time() + _NAME_CACHE_TTL)
        logger.debug("Fetched name for %s: %s", ticker_upper, result)
        return result

    except Exception as e:
        logger.warning(
            "Name fetch failed for %s: %s — using fallback '%s'",
            ticker_upper, e, fallback,
        )
        _NAME_CACHE[cache_key] = (fallback, time.time() + 3600)  # shorter retry
        return fallback


def _download_with_retry(
    tickers: str,
    period: str,
    max_retries: int = API_MAX_RETRIES,
    backoff_base: float = API_RETRY_BACKOFF_BASE,
) -> pd.DataFrame:
    """
    Download data from yfinance with exponential backoff retry logic.

    Args:
        tickers: Space-separated ticker symbols (e.g., "VHY.AX VAS.AX")
        period: yfinance period string (e.g., "3mo", "max", "1y")
        max_retries: Maximum number of retry attempts
        backoff_base: Base for exponential backoff (delay = backoff_base ^ attempt)

    Returns:
        DataFrame on success, empty DataFrame on failure after all retries
    """
    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers,
                period=period,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
            )
            logger.debug(
                "Download succeeded for %d tickers, period=%s",
                len(tickers.split()) if isinstance(tickers, str) else len(tickers),
                period,
            )
            return df
        except Exception as e:
            is_last_attempt = attempt == max_retries - 1
            if is_last_attempt:
                logger.warning(
                    "Download failed after %d attempts (period=%s): %s",
                    max_retries, period, e,
                )
                return pd.DataFrame()
            else:
                delay = backoff_base ** attempt
                logger.debug(
                    "Download attempt %d/%d failed, retrying in %ss (period=%s): %s",
                    attempt + 1, max_retries, delay, period, e,
                )
                time.sleep(delay)


def _extract_close(bulk_df: pd.DataFrame, ticker_yf: str) -> pd.Series:
    """
    Safely pull a single ticker's Close series from a yf.download() result.

    yfinance MultiIndex layout varies by version and ticker count:
      - Single ticker              → flat columns ['Close', 'Open', ...]
      - Multi, group_by='ticker'  → MultiIndex (ticker, field)
      - Multi, group_by='column'  → MultiIndex (field, ticker)
    We try all layouts and return empty Series rather than crash.
    """
    if bulk_df is None or bulk_df.empty:
        return pd.Series(dtype=float)

    cols = bulk_df.columns

    if not isinstance(cols, pd.MultiIndex):
        # Flat — single ticker download
        return bulk_df["Close"].dropna() if "Close" in cols else pd.Series(dtype=float)

    # Layout A: (ticker, field)
    if (ticker_yf, "Close") in cols:
        return bulk_df[(ticker_yf, "Close")].dropna()
    # Layout B: (field, ticker)
    if ("Close", ticker_yf) in cols:
        return bulk_df[("Close", ticker_yf)].dropna()
    # Layout C: base ticker without exchange suffix
    base = ticker_yf.split(".")[0]
    if (base, "Close") in cols:
        return bulk_df[(base, "Close")].dropna()
    if ("Close", base) in cols:
        return bulk_df[("Close", base)].dropna()

    logger.warning("No Close column for %s — cols sample: %s", ticker_yf, list(cols[:6]))
    return pd.Series(dtype=float)


def fetch_live(holdings: list[dict], hist_period: str = "3mo") -> dict:
    """
    Fetch live prices, history, dividends and per-tranche P&L for all holdings.

    Strategy:
      - yf.download() × 2  (period + max) for all tickers at once — fast
      - yf.Ticker.fast_info per ticker for intraday quote during market hours
      - yf.Ticker.history per ticker for dividends (only column download drops)
      - Historical close used as price fallback when market is closed

    Computation delegated to engine:
      - compute_holding_pnl()  for market-value / P&L metrics
      - compute_tranche_pnl()  for per-tranche history
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

    # ── Bulk downloads with retry logic ───────────────────────────────────────
    multi_period = _download_with_retry(tickers_str, period=hist_period)
    multi_full   = _download_with_retry(tickers_str, period="max")

    enriched:  list[dict] = []
    histories: dict       = {}

    for h in holdings:
        ticker    = h["ticker"]
        ticker_yf = h["ticker_yf"]
        try:
            # ── Extract history series ────────────────────────────────────────
            close_period = _extract_close(multi_period, ticker_yf)
            close_full   = _extract_close(multi_full,   ticker_yf)

            # Normalise index to tz-naive datetime
            if not close_period.empty:
                close_period.index = pd.to_datetime(close_period.index).tz_localize(None)
            if not close_full.empty:
                close_full.index = pd.to_datetime(close_full.index).tz_localize(None)

            # ── Period history → normalised price chart ───────────────────────
            if not close_period.empty:
                df_p = close_period.reset_index()
                df_p.columns = ["Date", "Close"]
                histories[ticker] = df_p.to_dict("records")

            # ── Price: fast_info (intraday) with historical close as fallback ─
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
                "%-6s  fi_last=%6.3f  hist_last=%s  hist_prev=%s"
                "  using_last=%.3f  using_prev=%.3f",
                ticker,
                fi_last,
                f"{hist_last:.3f}" if hist_last else "N/A",
                f"{hist_prev:.3f}" if hist_prev else "N/A",
                last_price,
                prev_close,
            )

            # ── P&L metrics via engine ────────────────────────────────────────
            _pnl        = compute_holding_pnl(h, last_price, prev_close)
            mkt_value   = _pnl["mkt_value"]
            pnl         = _pnl["pnl"]
            pnl_pct     = _pnl["pnl_pct"]
            day_chg     = _pnl["day_chg"]
            day_chg_pct = _pnl["day_chg_pct"]
            day_pnl     = _pnl["day_pnl"]

            # ── Dividends (individual Ticker — bulk download drops this) ──────
            try:
                hist_raw = tk.history(period="max", auto_adjust=False)
                div_s = (
                    hist_raw["Dividends"]
                    if not hist_raw.empty and "Dividends" in hist_raw.columns
                    else pd.Series(dtype=float)
                )
            except Exception:
                div_s = pd.Series(dtype=float)

            cutoff     = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            annual_div = round(float(div_s[div_s.index >= cutoff].sum()) * h["total_shares"], 2)
            total_div  = round(float(div_s.sum()) * h["total_shares"], 2)
            div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0, 2)

            # ── Per-tranche P&L history via engine ────────────────────────────
            tranche_data: list[dict] = []
            if not close_full.empty:
                tranche_data = compute_tranche_pnl(close_full, h.get("buy_tranches", []))
            else:
                logger.warning("%s: close_full empty — no P&L tranche data", ticker)

            logger.info(
                "%-6s  pnl=%+.2f (%+.2f%%)  day=%+.2f  tranches=%d",
                ticker, pnl, pnl_pct, day_pnl, len(tranche_data),
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
                "last_price":  h["avg_cost"], "prev_close":  h["avg_cost"],
                "day_high":    h["avg_cost"], "day_low":     h["avg_cost"],
                "day_chg": 0, "day_chg_pct": 0, "day_pnl": 0,
                "mkt_value":   round(h["total_shares"] * h["avg_cost"], 2),
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
    logger.info(
        "Done — %d enriched, %d with history, cached %ds",
        len(enriched), len(histories), CACHE_TTL_SECONDS,
    )
    return result