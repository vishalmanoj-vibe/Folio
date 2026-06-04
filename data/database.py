# data/database.py
import logging
import os
import sqlite3

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    """Opens and returns a sqlite3 connection to DB_PATH with row_factory set and optimized pragmas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Advanced Pragmas for concurrency and performance
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


_DB_INITIALIZED = False


def init_db():
    """Initialises the database schema and logs the action."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    conn = get_connection()
    try:
        # 1. Transactions (Legacy support)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT    NOT NULL,
                ticker     TEXT    NOT NULL,
                shares     REAL    NOT NULL,
                price      REAL    NOT NULL,
                date       TEXT    NOT NULL,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Assets (Ticker Master Registry)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                ticker      TEXT PRIMARY KEY,
                name        TEXT,
                category    TEXT,
                market      TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Watchlist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker      TEXT PRIMARY KEY,
                added_date  TEXT NOT NULL,
                notes       TEXT DEFAULT '',
                order_index INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. ETF Metadata (Sector/Geo Weights)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_metadata (
                ticker      TEXT NOT NULL,
                meta_type   TEXT NOT NULL,   -- 'sector' or 'geo'
                category    TEXT NOT NULL,   -- e.g. 'Technology', 'Australia'
                weight      REAL NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, meta_type, category)
            )
        """)

        # 5. ETF Holdings Attempts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_holdings_attempts (
                ticker       TEXT PRIMARY KEY,
                last_attempt TEXT DEFAULT CURRENT_TIMESTAMP,
                last_error   TEXT
            )
        """)

        # 5b. ETF Holdings URLs (user-provided source overrides)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_holdings_urls (
                ticker      TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Price History (OHLC)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume REAL,
                dividends REAL DEFAULT 0,
                fetched_at TEXT,
                UNIQUE(ticker, date)
            );
        """)

        # 7. History Metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history_meta (
                ticker       TEXT PRIMARY KEY,
                first_date   TEXT,
                last_date    TEXT,
                last_fetched TEXT,
                period       TEXT
            )
        """)

        # 8. Market Prices (Computed Metrics Snapshot)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_prices (
                ticker           TEXT PRIMARY KEY,
                last_price       REAL,
                day_chg          REAL,
                day_chg_pct      REAL,
                day_pnl          REAL,
                mkt_value        REAL,
                pnl              REAL,
                pnl_pct          REAL,
                annual_div       REAL,
                realized_div     REAL,
                div_yield        REAL,
                div_frequency    TEXT,
                last_div_amount  REAL,
                last_div_date    TEXT,
                next_div_date    TEXT,
                payout_date      TEXT,
                fetched_at       TEXT NOT NULL
            )
        """)

        # 9. Intraday Snapshots
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intraday_snapshots (
                ticker       TEXT NOT NULL,
                recorded_at  TEXT NOT NULL,
                price        REAL NOT NULL,
                session_date TEXT NOT NULL,
                PRIMARY KEY (ticker, recorded_at)
            )
        """)

        # 10. Predictions Cache
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions_cache (
                cache_key    TEXT PRIMARY KEY,
                dates        TEXT NOT NULL, -- JSON
                yhat         TEXT NOT NULL, -- JSON
                yhat_lower   TEXT NOT NULL, -- JSON
                yhat_upper   TEXT NOT NULL, -- JSON
                fitted_last  REAL,
                computed_at  TEXT NOT NULL
            )
        """)

        # 11. Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_etf_meta_ticker ON etf_metadata(ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_date ON watchlist(added_date)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_ticker_date ON price_history(ticker, date)"
        )
        # 9. Worker Tasks (Task Queue)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS worker_tasks (
                task_id      TEXT PRIMARY KEY,
                task_type    TEXT NOT NULL,
                payload      TEXT, -- JSON
                status       TEXT DEFAULT 'pending',
                priority     INTEGER DEFAULT 5,
                created_at   TEXT NOT NULL,
                completed_at TEXT,
                result       TEXT -- JSON
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_worker_tasks_poll ON worker_tasks(status, priority, created_at)"
        )

        # 10. Signal Results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_results (
                ticker            TEXT PRIMARY KEY,
                signal            TEXT NOT NULL,
                score             REAL NOT NULL,
                confidence        REAL,
                reasons           TEXT, -- JSON
                indicators        TEXT, -- JSON
                ai_explanation    TEXT,
                generated_at      TEXT NOT NULL,
                hysteresis_forced INTEGER DEFAULT 0
            )
        """)

        # 11. Watchlist Signal Results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_signal_results (
                ticker            TEXT PRIMARY KEY,
                signal            TEXT NOT NULL,
                score             REAL NOT NULL,
                confidence        REAL,
                reasons           TEXT, -- JSON
                indicators        TEXT, -- JSON
                ai_explanation    TEXT,
                generated_at      TEXT NOT NULL,
                hysteresis_forced INTEGER DEFAULT 0
            )
        """)

        # 12. Benchmark Data
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_data (
                symbol     TEXT PRIMARY KEY,
                label      TEXT NOT NULL,
                history    TEXT, -- JSON
                fetched_at TEXT NOT NULL
            )
        """)

        # 13. App Metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 14. User Settings (Investor Profile)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 15. Sentiment Cache (News Sentiment per ticker)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_cache (
                ticker       TEXT PRIMARY KEY,
                sentiment    TEXT NOT NULL,
                score        REAL NOT NULL,
                headline_1   TEXT,
                headline_2   TEXT,
                rationale    TEXT,
                fetched_at   TEXT NOT NULL
            )
        """)

        conn.commit()

        # 12. Migrations — Add missing columns to existing tables
        try:
            # Check for last_div_date in market_prices
            cursor = conn.execute("PRAGMA table_info(market_prices)")
            columns = [row[1] for row in cursor.fetchall()]
            if "last_div_date" not in columns:
                logger.info("Migrating market_prices: Adding last_div_date column")
                conn.execute("ALTER TABLE market_prices ADD COLUMN last_div_date TEXT")
            if "last_price" not in columns:
                logger.info("Migrating market_prices: Adding last_price column")
                conn.execute("ALTER TABLE market_prices ADD COLUMN last_price REAL")
            conn.commit()
        except Exception as e:
            logger.warning(f"Migration for market_prices failed: {e}")

        # 13. Migration — Add dividends to price_history if missing
        try:
            cursor = conn.execute("PRAGMA table_info(price_history)")
            columns = [row[1] for row in cursor.fetchall()]
            if "dividends" not in columns:
                logger.info("Migrating price_history: Adding dividends column")
                conn.execute("ALTER TABLE price_history ADD COLUMN dividends REAL DEFAULT 0")
                conn.commit()
        except Exception as e:
            logger.warning(f"Migration for price_history failed: {e}")

        # 14. Migration — Ensure history_meta has all columns
        try:
            cursor = conn.execute("PRAGMA table_info(history_meta)")
            columns = [row[1] for row in cursor.fetchall()]
            if "period" not in columns:
                conn.execute("ALTER TABLE history_meta ADD COLUMN period TEXT")
                conn.commit()
        except Exception as e:
            logger.warning(f"Migration for history_meta failed: {e}")

        # 15. Migration — Create etf_holdings_urls if missing (existing DBs)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS etf_holdings_urls (
                    ticker      TEXT PRIMARY KEY,
                    url         TEXT NOT NULL,
                    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        except Exception as e:
            logger.warning(f"Migration for etf_holdings_urls failed: {e}")

        # 16. Migration — Add order_index to watchlist if missing
        try:
            cursor = conn.execute("PRAGMA table_info(watchlist)")
            columns = [row[1] for row in cursor.fetchall()]
            if "order_index" not in columns:
                logger.info("Migrating watchlist: Adding order_index column")
                conn.execute("ALTER TABLE watchlist ADD COLUMN order_index INTEGER DEFAULT 0")
                conn.commit()
        except Exception as e:
            logger.warning(f"Migration for watchlist order_index failed: {e}")

        # 13. Legacy JSON Migration
        migrate_json_to_sqlite()

        _DB_INITIALIZED = True
        logger.info(f"Database initialised at {DB_PATH}")
    finally:
        conn.close()


def get_db_path():
    """Returns the absolute path to the database file."""
    return DB_PATH


def migrate_json_to_sqlite():
    """Seamlessly migrates data from legacy JSON caches to SQLite on first run."""
    import glob
    import json
    from datetime import datetime

    snapshot_path = "data/cache/portfolio_snapshot.json"
    predictions_path = "data/cache/predictions.json"
    intraday_files = glob.glob("data/cache/intraday_*.json")

    # Check if there is anything to migrate
    if not (os.path.exists(snapshot_path) or os.path.exists(predictions_path) or intraday_files):
        return

    conn = get_connection()
    try:
        # Start a single transaction for the entire migration
        conn.execute("BEGIN TRANSACTION")

        # A. Market Prices (portfolio_snapshot.json)
        row = conn.execute("SELECT COUNT(*) FROM market_prices").fetchone()
        if row[0] == 0 and os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                data = json.load(f)
                holdings = data.get("holdings", [])
                fetched_at = data.get("fetched_at", datetime.now().isoformat())
                for h in holdings:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO market_prices (
                            ticker, last_price, day_chg, day_chg_pct, day_pnl, mkt_value, pnl, pnl_pct,
                            annual_div, realized_div, div_yield, div_frequency,
                            last_div_amount, next_div_date, payout_date, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            h["ticker"],
                            h.get("last_price"),
                            h.get("day_chg"),
                            h.get("day_chg_pct"),
                            h.get("day_pnl"),
                            h.get("mkt_value"),
                            h.get("pnl"),
                            h.get("pnl_pct"),
                            h.get("annual_div"),
                            h.get("realized_div"),
                            h.get("div_yield"),
                            h.get("div_frequency"),
                            h.get("last_div_amount"),
                            h.get("next_div_date"),
                            h.get("payout_date"),
                            fetched_at,
                        ),
                    )

        # B. Intraday Snapshots (intraday_YYYY-MM-DD.json)
        row = conn.execute("SELECT COUNT(*) FROM intraday_snapshots").fetchone()
        if row[0] == 0:
            for f_path in intraday_files:
                with open(f_path) as f:
                    session_data = json.load(f)
                    date_str = (
                        os.path.basename(f_path).replace("intraday_", "").replace(".json", "")
                    )
                    for ticker, points in session_data.items():
                        for p in points:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO intraday_snapshots (ticker, recorded_at, price, session_date)
                                VALUES (?, ?, ?, ?)
                            """,
                                (ticker, p["Date"], p["Close"], date_str),
                            )

        # C. Predictions Cache (predictions.json)
        row = conn.execute("SELECT COUNT(*) FROM predictions_cache").fetchone()
        if row[0] == 0 and os.path.exists(predictions_path):
            with open(predictions_path) as f:
                cache = json.load(f)
                for key, res in cache.items():
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO predictions_cache (
                            cache_key, dates, yhat, yhat_lower, yhat_upper, fitted_last, computed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            key,
                            json.dumps(res["dates"]),
                            json.dumps(res["yhat"]),
                            json.dumps(res["yhat_lower"]),
                            json.dumps(res["yhat_upper"]),
                            res.get("fitted_last", 0.0),
                            res.get("computed_at", ""),
                        ),
                    )

        # Commit all changes
        conn.execute("COMMIT")
        logger.info("Successfully committed migration data to SQLite")

        # D. Post-commit Verification & Cleanup
        # Only delete files if we are sure the data is in the DB
        if os.path.exists(snapshot_path):
            count = conn.execute("SELECT COUNT(*) FROM market_prices").fetchone()[0]
            if count > 0:
                os.remove(snapshot_path)
                logger.info("Cleaned up portfolio_snapshot.json")

        if os.path.exists(predictions_path):
            count = conn.execute("SELECT COUNT(*) FROM predictions_cache").fetchone()[0]
            if count > 0:
                os.remove(predictions_path)
                logger.info("Cleaned up predictions.json")

        for f_path in intraday_files:
            date_str = os.path.basename(f_path).replace("intraday_", "").replace(".json", "")
            count = conn.execute(
                "SELECT COUNT(*) FROM intraday_snapshots WHERE session_date = ?", (date_str,)
            ).fetchone()[0]
            if count > 0:
                os.remove(f_path)
                logger.info(f"Cleaned up {f_path}")

    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Migration failed, rolled back: {e}")
    finally:
        conn.close()


def enqueue_task(task_type: str, payload: dict | None = None, priority: int = 5) -> str:
    """Insert a new task into the worker_tasks table. Returns the task_id."""
    import json
    import uuid
    from datetime import datetime

    task_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO worker_tasks (task_id, task_type, payload, status, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                task_id,
                task_type,
                json.dumps(payload) if payload else None,
                "pending",
                priority,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        return task_id
    finally:
        conn.close()
