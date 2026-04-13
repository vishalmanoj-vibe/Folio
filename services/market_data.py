import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from services.cache import get_cache, set_cache

logger    = logging.getLogger(__name__)
CACHE_TTL = 60   # seconds


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

    # ── Bulk downloads (auto_adjust=False preserves Dividends column) ─────────
    try:
        multi_period = yf.download(
            tickers_str, period=hist_period,
            group_by="ticker", auto_adjust=False, progress=False,
        )
    except Exception as exc:
        logger.warning("Bulk period download failed: %s", exc)
        multi_period = pd.DataFrame()

    try:
        multi_full = yf.download(
            tickers_str, period="max",
            group_by="ticker", auto_adjust=False, progress=False,
        )
    except Exception as exc:
        logger.warning("Bulk full download failed: %s", exc)
        multi_full = pd.DataFrame()

    enriched:  list[dict] = []
    histories: dict        = {}

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
            # fast_info returns 0.0 outside market hours — guard with > 0
            tk = yf.Ticker(ticker_yf)
            fi = tk.fast_info

            fi_last  = fi.get("last_price")      or 0.0
            fi_prev  = fi.get("previous_close")  or 0.0
            fi_high  = fi.get("day_high")        or 0.0
            fi_low   = fi.get("day_low")         or 0.0

            # Use last two rows of full history for reliable closed-market prices
            hist_last  = float(close_full.iloc[-1])  if len(close_full) >= 1 else None
            hist_prev  = float(close_full.iloc[-2])  if len(close_full) >= 2 else None

            last_price = float(fi_last if fi_last > 0 else (hist_last or h["avg_cost"]))
            prev_close = float(fi_prev if fi_prev > 0 else (hist_prev or last_price))
            day_high   = float(fi_high if fi_high > 0 else last_price)
            day_low    = float(fi_low  if fi_low  > 0 else last_price)

            logger.info(
                "%-6s  fi_last=%6.3f  hist_last=%s  hist_prev=%s  using_last=%.3f  using_prev=%.3f",
                ticker,
                fi_last,
                f"{hist_last:.3f}" if hist_last else "N/A",
                f"{hist_prev:.3f}" if hist_prev else "N/A",
                last_price,
                prev_close,
            )

            # ── Derived day + portfolio metrics ───────────────────────────────
            day_chg     = round(last_price - prev_close, 4)
            day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)
            mkt_value   = round(h["total_shares"] * last_price, 2)
            pnl         = round(mkt_value - h["total_cost"], 2)
            pnl_pct     = round((pnl / h["total_cost"] * 100) if h["total_cost"] else 0, 2)
            day_pnl     = round(day_chg * h["total_shares"], 2)

            # ── Dividends (needs individual Ticker — bulk drops this column) ──
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

            # ── Per-tranche P&L history ───────────────────────────────────────
            tranche_data: list[dict] = []
            if not close_full.empty:
                for tr in h.get("buy_tranches", []):
                    buy_date = pd.to_datetime(tr["date"])
                    mask = close_full.index >= buy_date
                    if not mask.any():
                        logger.debug("%s tranche %s: no history after buy date", ticker, tr["date"])
                        continue
                    sub   = close_full[mask].copy()
                    pnl_s = (sub - tr["price"]) * tr["shares"]
                    pct_s = (sub - tr["price"]) / tr["price"] * 100
                    tranche_data.append({
                        "dates":     [d.strftime("%Y-%m-%d") for d in sub.index],
                        "pnl":       [round(v, 2) for v in pnl_s.tolist()],
                        "pct":       [round(v, 2) for v in pct_s.tolist()],
                        "shares":    float(tr["shares"]),
                        "buy_price": float(tr["price"]),
                        "buy_date":  tr["date"],
                    })
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
                "day_chg":     0, "day_chg_pct": 0, "day_pnl": 0,
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
    set_cache(cache_key, result, ttl=CACHE_TTL)
    logger.info("Done — %d enriched, %d with history, cached %ds", len(enriched), len(histories), CACHE_TTL)
    return result