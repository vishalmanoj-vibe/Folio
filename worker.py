# worker.py
"""
Folio Background Worker
=======================
Handles all network-bound tasks:
1. Scheduled live price refreshes (every 5m during market hours).
2. On-demand tasks (history fetches, signal generation, benchmarks).

Communicates with Dash process via SQLite (worker_tasks table).
"""

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime

import pandas as pd

# Setup logging
from config.logging import setup_logging
from core.engine import build_holdings
from data.cache_manager import save_live_prices
from data.database import get_connection, init_db
from data.repository import HistoryRepository, PortfolioRepository
from services.ai_engine import analyze_signals
from services.market.data_fetcher import fetch_benchmarks, fetch_live, fetch_ticker_history
from services.market.market_status import is_market_open, time_until_market_open
from services.strategy_engine import generate_portfolio_signals

setup_logging()
logger = logging.getLogger("worker")

from dotenv import load_dotenv

load_dotenv()

# Load GEMINI_API_KEY from database metadata if not in environment
if not os.environ.get("GEMINI_API_KEY"):
    try:
        from data.repository import PortfolioRepository

        db_key = PortfolioRepository().get_gemini_api_key()
        if db_key:
            os.environ["GEMINI_API_KEY"] = db_key
            logger.info("Successfully loaded GEMINI_API_KEY from database metadata.")
    except Exception as e:
        logger.debug(f"Could not load GEMINI_API_KEY from database: {e}")

# ── Task Handlers ────────────────────────────────────────────────────────────


def handle_fetch_history(payload: dict):
    """Fetch history for a ticker and period."""
    ticker = payload.get("ticker")
    period = payload.get("period", "max")
    if not ticker:
        return {"error": "Missing ticker"}

    logger.info(f"Task: Fetching history for {ticker} ({period})")
    results = fetch_ticker_history(ticker, period)
    return {"status": "success", "count": len(results)}


def handle_generate_signals(payload: dict):
    """Run strategy engine and AI analysis for tickers."""
    tickers = payload.get("tickers", [])
    scope = payload.get("scope", "portfolio")  # 'portfolio' or 'watchlist'

    if not tickers:
        return {"error": "No tickers provided"}

    logger.info(f"Task: Generating signals for {len(tickers)} tickers (scope: {scope})")

    # 1. Build Context
    from data.repository import PortfolioRepository
    from services.market.data_fetcher import extract_close, get_full_history_cache

    # We need holdings data with ticker_yf and avg_cost
    repo = PortfolioRepository()
    if scope == "portfolio":
        holdings = build_holdings(repo.load_transactions())
    else:
        from data.watchlist_repository import WatchlistRepository

        w_repo = WatchlistRepository()
        holdings = w_repo.load_watchlist_holdings()

    multi_full = get_full_history_cache(holdings)

    # Ensure we have enough history for technical indicators (min 220 days) for ALL tickers
    missing_depth = []
    if multi_full.empty:
        missing_depth = [h["ticker"] for h in holdings]
    else:
        for h in holdings:
            t_yf = h.get("ticker_yf", h["ticker"] + ".AX")
            s = extract_close(multi_full, t_yf)
            if s.empty or len(s.dropna()) < 220:
                missing_depth.append(h["ticker"])

    if missing_depth:
        logger.info(
            "Signal history missing or insufficient for %d tickers: %s. Fetching...",
            len(missing_depth),
            missing_depth,
        )
        # Fetch only what's missing to be efficient, but force_fetch=True to ensure it hits yfinance if stale
        missing_holdings = [h for h in holdings if h["ticker"] in missing_depth]
        from services.market.data_fetcher import fetch_portfolio_series

        fetch_portfolio_series(missing_holdings, "max", force_fetch=True)
        # Re-load full cache
        multi_full = get_full_history_cache(holdings)

    if multi_full.empty:
        logger.warning("Could not retrieve any history for signal generation.")
        return {"error": "Insufficient market data history for technical signals"}
    # Load previous signals for hysteresis
    conn = get_connection()
    prev_signals = {}
    try:
        rows = conn.execute("SELECT ticker, signal FROM signal_results").fetchall()
        for r in rows:
            prev_signals[r["ticker"]] = {"signal": r["signal"]}
    finally:
        conn.close()

    # 2. Strategy Engine (incorporating investor profile settings)
    from data.settings_repository import get_all_settings
    from services.strategy_engine import get_profile_weights

    settings = get_all_settings()
    weights = get_profile_weights(
        investment_goal=settings.get("investment_goal", "Balanced"),
        risk_tolerance=settings.get("risk_tolerance", "Moderate"),
    )
    signals = generate_portfolio_signals(multi_full, holdings, prev_signals, weights=weights)

    # 3. AI Analysis
    ai_results = analyze_signals(signals)

    # 3. Persist to SQLite
    table = "signal_results" if scope == "portfolio" else "watchlist_signal_results"

    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        for ticker, sig in signals.items():
            ai_res = ai_results.get(ticker, {})

            conn.execute(
                f"""
                INSERT OR REPLACE INTO {table} (
                    ticker, signal, score, confidence, reasons, indicators,
                    ai_explanation, generated_at, hysteresis_forced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ticker,
                    sig["signal"],
                    sig["score"],
                    sig.get("confidence"),
                    json.dumps(sig["reasons"]),
                    json.dumps(sig["indicators"]),
                    json.dumps(ai_res) if ai_res else None,
                    now,
                    1 if sig.get("hysteresis_forced") else 0,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    # 4. News Sentiment Analysis (runs as part of signal generation)
    from services.sentiment_service import get_sentiment

    for ticker in signals.keys():
        try:
            get_sentiment(ticker, force_refresh=True)
        except Exception as e:
            logger.error(f"Failed to fetch sentiment for {ticker} in batch: {e}")

    return {"status": "success", "tickers": list(signals.keys()), "scope": scope}


def handle_generate_ai_response(payload: dict):
    """Generate Assistant/Research chat response using Gemini (async)."""
    messages = payload.get("messages", [])
    context = payload.get("context", {})
    ticker = payload.get("ticker", "General")

    if not messages:
        return {"error": "No chat history provided"}

    logger.info(f"Task: Generating AI response for {ticker}")

    # We wrap the Gemini call in a thread to enforce a 45s timeout
    result_container = {"response": None, "error": None}

    def _call_gemini():
        try:
            import pandas as pd

            from data.repository import HistoryRepository
            from services.research_service import get_ai_response

            # Enrich context with histories for technical analysis and performance context
            h_repo = HistoryRepository()
            holdings = context.get("holdings", [])
            tickers = [h["ticker"] for h in holdings]

            if tickers:
                # Fetch 14 days of history to ensure we have enough for technicals and 7d performance
                histories = {}
                cutoff = (pd.Timestamp.now() - pd.Timedelta(days=14)).strftime("%Y-%m-%d")
                for t in tickers:
                    h_list = h_repo.load_history(t, from_date=cutoff)
                    if h_list:
                        histories[t] = h_list
                context["histories"] = histories

            response = get_ai_response(messages, context, ticker)
            result_container["response"] = response
        except Exception as e:
            result_container["error"] = str(e)

    t = threading.Thread(target=_call_gemini)
    t.start()
    t.join(timeout=45.0)

    if t.is_alive():
        logger.warning(f"AI Task for {ticker} timed out after 45s")
        return {"error": "Assistant timed out (45s limit reached)"}

    if result_container["error"]:
        return {"error": result_container["error"]}

    return {"status": "success", "response": result_container["response"]}


def handle_fetch_benchmarks(payload: dict):
    """Fetch S&P 500 and ASX 200 history."""
    period = payload.get("period", "max")
    logger.info(f"Task: Fetching benchmarks ({period})")

    results = fetch_benchmarks(period)

    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        for label, history in results.items():
            # Map label back to symbol (supporting defaults and preset benchmark options)
            preset_labels = {
                "^GSPC": "S&P 500",
                "^AXJO": "ASX 200",
                "^NDX": "Nasdaq 100",
                "URTH": "MSCI World",
            }
            symbol = next((k for k, v in preset_labels.items() if v == label), label)

            conn.execute(
                """
                INSERT OR REPLACE INTO benchmark_data (
                    symbol, label, history, fetched_at
                ) VALUES (?, ?, ?, ?)
            """,
                (symbol, label, json.dumps(history), now),
            )
        conn.commit()
    finally:
        conn.close()

    return {"status": "success", "benchmarks": list(results.keys())}


def handle_generate_report(payload: dict):
    """Generate weekly PDF report (async)."""
    # Note: We don't need a huge payload. We can rebuild context from DB.
    logger.info("Task: Generating weekly report")

    try:
        import base64

        from core.engine import build_holdings
        from data.repository import PortfolioRepository
        from services.market.data_fetcher import get_full_history_cache
        from services.report_service import generate_weekly_report

        # 1. Build context from DB
        repo = PortfolioRepository()
        txns = repo.load_transactions()
        holdings = build_holdings(txns)

        # Fetch live prices & historical metrics for technical report generation
        from services.market.data_fetcher import fetch_live, fetch_portfolio_history

        live_data, _, _ = fetch_live(holdings)
        enriched_holdings = live_data.get("holdings", [])
        fetched_at = live_data.get("fetched_at", "Unknown")

        # Fetch histories for technical signals & P&L trend charts
        histories = fetch_portfolio_history(enriched_holdings, "max")

        portfolio_data = {
            "holdings": enriched_holdings,
            "fetched_at": fetched_at,
            "histories": histories,
        }

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return {"error": "Missing GEMINI_API_KEY"}

        pdf_bytes = generate_weekly_report(portfolio_data, api_key)
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return {"status": "success", "pdf_b64": b64}
    except Exception as e:
        logger.error(f"Report task failed: {e}")
        return {"error": str(e)}


def handle_generate_prediction(payload: dict):
    """Generate portfolio return forecast using Prophet."""
    dates = payload.get("dates", [])
    values = payload.get("values", [])
    horizon = payload.get("horizon", "3mo")

    if not dates or not values:
        return {"error": "Missing dates or values"}

    logger.info(f"Task: Generating prediction forecast (horizon: {horizon})")
    # Lazy import to keep worker startup fast
    from services.prediction_service import get_forecast

    result = get_forecast(dates, values, horizon)

    if not result:
        return {"error": "Forecast generation failed or returned empty"}

    return {"status": "success"}


def handle_maintenance(payload: dict):
    """Perform periodic maintenance: cache cleanup, AI memory, and history refreshes."""
    logger.info("Task: Running background maintenance...")

    # 1. Clear old intraday caches
    from services.market.session_cache import clear_old_caches

    clear_old_caches(keep_days=1)

    # 2. Run AI startup maintenance (summarization)
    api_key = payload.get("gemini_api_key")
    if api_key:
        from services.research_memory import run_startup_maintenance

        run_startup_maintenance(api_key)

    # 3. Refresh watchlist histories
    from data.watchlist_repository import WatchlistRepository

    WatchlistRepository().refresh_all_histories()

    # 4. Refresh portfolio histories
    from data.repository import PortfolioRepository
    from services.market.data_fetcher import fetch_ticker_history

    txns = PortfolioRepository().load_transactions()
    tickers = {t["ticker"] for t in txns}
    for t in tickers:
        # fetch_ticker_history internally checks is_stale (24h gate)
        fetch_ticker_history(t, "max")

    return {"status": "success"}


def handle_scrape_holdings(payload: dict):
    """Fetch ETF holdings breakdown from provider websites."""
    ticker = payload.get("ticker")
    if not ticker:
        return {"error": "Missing ticker"}

    logger.info(f"Task: Scraping holdings for {ticker}")
    from services.market.holdings_fetcher import fetch_holdings

    # Important: allow_scrape=True to actually run the scrape in the worker process
    results = fetch_holdings(ticker, allow_scrape=True)

    if not results:
        return {"error": "Scrape failed or returned no holdings"}
    return {"status": "success", "count": len(results)}


def handle_refresh_portfolio(payload: dict):
    """Immediate portfolio refresh triggered by UI."""
    logger.info("Task: Immediate portfolio refresh triggered by UI")
    repo = PortfolioRepository()
    txns = repo.load_transactions()
    holdings = build_holdings(txns)
    if holdings:
        fetch_live(holdings, record_snapshots=True)
    return {"status": "success"}


def handle_sentiment_batch(payload: dict):
    """Batch sentiment refresh."""
    tickers = payload.get("tickers", [])
    if not tickers:
        return {"error": "No tickers provided"}

    logger.info(f"Task: Analyzing news sentiment for {len(tickers)} tickers")
    from services.sentiment_service import get_sentiment

    results = {}
    for t in tickers:
        try:
            res = get_sentiment(t, force_refresh=True)
            results[t] = res
        except Exception as e:
            logger.error(f"Failed to get sentiment for {t}: {e}")
            results[t] = {"error": str(e)}

    return {"status": "success", "results": results}


TASK_HANDLERS = {
    "fetch_history": handle_fetch_history,
    "generate_signals": handle_generate_signals,
    "scrape_holdings": handle_scrape_holdings,
    "fetch_benchmarks": handle_fetch_benchmarks,
    "generate_ai_response": handle_generate_ai_response,
    "generate_report": handle_generate_report,
    "generate_prediction": handle_generate_prediction,
    "maintenance": handle_maintenance,
    "refresh_portfolio": handle_refresh_portfolio,
    "sentiment_batch": handle_sentiment_batch,
}

# ── Main Worker Loops ────────────────────────────────────────────────────────


def reset_stale_tasks():
    """On startup, reset pending/running tasks older than 10 mins to failed."""
    logger.info("Maintenance: Resetting stale tasks...")
    conn = get_connection()
    try:
        cutoff = (datetime.now() - pd.Timedelta(minutes=10)).isoformat()
        cursor = conn.execute(
            """
            UPDATE worker_tasks
            SET status = 'failed', result = '{"error": "Task timed out or worker restarted"}'
            WHERE status IN ('pending', 'running') AND created_at < ?
        """,
            (cutoff,),
        )
        if cursor.rowcount > 0:
            logger.info(f"Reset {cursor.rowcount} stale tasks to failed")
        conn.commit()
    finally:
        conn.close()


def prune_tasks():
    """On startup, delete completed/failed tasks older than 24 hours."""
    logger.info("Maintenance: Pruning old tasks...")
    conn = get_connection()
    try:
        cutoff = (datetime.now() - pd.Timedelta(hours=24)).isoformat()
        cursor = conn.execute(
            """
            DELETE FROM worker_tasks
            WHERE status IN ('complete', 'failed') AND completed_at < ?
        """,
            (cutoff,),
        )
        if cursor.rowcount > 0:
            logger.info(f"Pruned {cursor.rowcount} old tasks from queue")
        conn.commit()
    finally:
        conn.close()


def poll_tasks():
    """Check worker_tasks table for pending tasks."""
    conn = get_connection()
    try:
        # Fetch highest priority oldest task
        task = conn.execute("""
            SELECT * FROM worker_tasks
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """).fetchone()

        if not task:
            return

        task_id = task["task_id"]
        task_type = task["task_type"]
        payload = json.loads(task["payload"]) if task["payload"] else {}

        # Mark as running
        conn.execute("UPDATE worker_tasks SET status = 'running' WHERE task_id = ?", (task_id,))
        conn.commit()

        # Execute
        handler = TASK_HANDLERS.get(task_type)
        if not handler:
            result = {"error": f"Unknown task type: {task_type}"}
            status = "failed"
        else:
            try:
                result = handler(payload)
                status = "complete"
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                result = {"error": str(e)}
                status = "failed"

        # Mark as complete/failed
        conn.execute(
            """
            UPDATE worker_tasks
            SET status = ?, result = ?, completed_at = ?
            WHERE task_id = ?
        """,
            (status, json.dumps(result), datetime.now().isoformat(), task_id),
        )
        conn.commit()

    except Exception as e:
        logger.error(f"Polling loop error: {e}")
    finally:
        conn.close()


def run_worker():
    """Main worker entry point."""
    logger.info("Folio Worker starting up...")

    # 0. Initialize database schema
    init_db()

    # 1. Initial maintenance (Reset then Prune)
    reset_stale_tasks()
    prune_tasks()

    last_refresh = 0
    REFRESH_COOLDOWN = 300  # initial default — overridden by user settings each cycle

    # Map from policy string to seconds
    _POLICY_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "EOD": 86400,
    }

    while True:
        # ── Part A: Demand-driven Task Queue ───────────────────
        poll_tasks()

        # ── Part B: Time-driven Scheduled Fetch ───────────────
        now = time.time()
        if now - last_refresh >= REFRESH_COOLDOWN:
            try:
                # We always want at least one fetch on startup to populate empty caches
                if last_refresh == 0 or is_market_open(include_auction=True):
                    logger.info(
                        "Scheduled refresh: Fetching live prices (Startup or Market Open)..."
                    )

                    # Derive current holdings from transactions
                    repo = PortfolioRepository()
                    txns = repo.load_transactions()
                    holdings = build_holdings(txns)

                    if holdings:
                        # Perform refresh
                        fetch_live(holdings, record_snapshots=True)
                        logger.info(f"Refreshed {len(holdings)} holdings")

                    last_refresh = now

                    # Read user-configured refresh policy on each cycle
                    try:
                        from data.settings_repository import get_setting

                        policy = get_setting("data_refresh_policy", "5m") or "5m"
                        REFRESH_COOLDOWN = _POLICY_SECONDS.get(policy, 300)
                    except Exception:
                        REFRESH_COOLDOWN = 300  # fallback to 5m

                else:
                    wait_sec = time_until_market_open()
                    logger.debug(
                        f"Market closed. Next check in 10 minutes (or until open: {wait_sec:.0f}s)"
                    )
                    last_refresh = now
                    REFRESH_COOLDOWN = 600  # Check every 10m when closed
            except Exception as e:
                logger.error(f"Scheduled refresh failed: {e}")
                last_refresh = now  # Still back off to prevent tight loop failure

        time.sleep(2)  # Small sleep between polls


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.critical(f"Worker crashed: {e}")
