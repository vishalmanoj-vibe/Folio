# services/market/session_cache.py
import logging
from datetime import datetime

import pandas as pd

from data.database import get_connection

logger = logging.getLogger(__name__)


def record_snapshot(enriched_holdings: list[dict]):
    """
    Record the current price for all holdings into today's session cache in SQLite.

    This persistence layer ensures that the "Today" (1d) chart remains
    continuous even if the application is restarted during trading hours.
    """
    now_syd = pd.Timestamp.now(tz="Australia/Sydney")
    now_str = now_syd.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now_syd.strftime("%Y-%m-%d")

    # Snapshot cooldown (seconds). 290s allows for a 300s interval with slight jitter.
    COOLDOWN_SEC = 290

    conn = get_connection()
    try:
        updated = False
        for h in enriched_holdings:
            ticker = h["ticker"].upper()
            raw_price = h.get("last_price")

            if raw_price is None or not isinstance(raw_price, (int, float)):
                continue

            price = round(float(raw_price), 4)
            if price <= 0:
                continue

            # Check cooldown since last recorded point for this ticker
            row = conn.execute(
                "SELECT MAX(recorded_at) FROM intraday_snapshots WHERE ticker = ?", (ticker,)
            ).fetchone()

            should_record = False
            if not row or not row[0]:
                should_record = True
            else:
                last_date = pd.to_datetime(row[0]).tz_localize("Australia/Sydney")
                seconds_since = (now_syd - last_date).total_seconds()
                if seconds_since >= COOLDOWN_SEC:
                    should_record = True

            if should_record:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO intraday_snapshots (ticker, recorded_at, price, session_date)
                    VALUES (?, ?, ?, ?)
                """,
                    (ticker, now_str, price, today_str),
                )
                updated = True

        if updated:
            conn.commit()
    except Exception as e:
        logger.error("Failed to record session snapshot to SQLite: %s", e)
    finally:
        conn.close()


def backfill_session_cache(tickers_data: dict[str, pd.Series], start_limit: pd.Timestamp = None):
    """
    Backfill the session cache in SQLite with historical intraday data.
    """
    now_syd = pd.Timestamp.now(tz="Australia/Sydney")
    today_str = now_syd.strftime("%Y-%m-%d")

    if start_limit is None:
        start_limit = pd.Timestamp(f"{today_str} 10:00:00", tz="Australia/Sydney")
    elif start_limit.tzinfo is None:
        start_limit = start_limit.tz_localize("Australia/Sydney")

    conn = get_connection()
    try:
        added_count = 0
        for ticker, series in tickers_data.items():
            if series.empty:
                continue

            ticker = ticker.upper()
            for ts, price in series.items():
                try:
                    ts_ts = pd.Timestamp(ts)
                    if ts_ts.tzinfo is None:
                        ts_syd = ts_ts.tz_localize("Australia/Sydney")
                    else:
                        ts_syd = ts_ts.tz_convert("Australia/Sydney")
                except Exception:
                    ts_syd = pd.Timestamp(ts)

                if ts_syd < start_limit:
                    continue

                if price <= 0:
                    continue

                time_str = ts_syd.strftime("%Y-%m-%d %H:%M:%S")
                sess_date = ts_syd.strftime("%Y-%m-%d")

                conn.execute(
                    """
                    INSERT OR IGNORE INTO intraday_snapshots (ticker, recorded_at, price, session_date)
                    VALUES (?, ?, ?, ?)
                """,
                    (ticker, time_str, round(float(price), 4), sess_date),
                )
                added_count += 1

        conn.commit()
        if added_count > 0:
            logger.info("Backfilled session cache with %d points in SQLite", added_count)
    except Exception as e:
        logger.error("Failed to backfill session cache in SQLite: %s", e)
    finally:
        conn.close()


def get_session_history(ticker: str) -> pd.Series:
    """
    Retrieve the appropriate session points for a ticker from SQLite.
    If market is closed/weekend, returns the most recent trading session data.
    """
    from data.cache_manager import get_intraday
    from services.market.market_status import get_effective_session_context

    context = get_effective_session_context()
    session_date_str = context["effective_date"].strftime("%Y-%m-%d")

    return get_intraday(ticker, session_date_str)


def clear_old_caches(keep_days: int = 2):
    """Delete session caches older than keep_days from SQLite."""
    cutoff = (pd.Timestamp.now(tz="Australia/Sydney") - pd.Timedelta(days=keep_days)).strftime(
        "%Y-%m-%d"
    )

    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM intraday_snapshots WHERE session_date < ?", (cutoff,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info("Cleared %d old intraday snapshots from SQLite", cursor.rowcount)
    except Exception as e:
        logger.error("Failed to clear old intraday snapshots from SQLite: %s", e)
    finally:
        conn.close()
