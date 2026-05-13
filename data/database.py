# data/database.py
import sqlite3
import os
import logging
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT    NOT NULL,
                ticker     TEXT    NOT NULL,
                shares     REAL    NOT NULL,
                price      REAL    NOT NULL,
                date       TEXT    NOT NULL,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Assets (Ticker Master Registry)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                ticker      TEXT PRIMARY KEY,
                name        TEXT,
                category    TEXT,
                market      TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. Watchlist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker      TEXT PRIMARY KEY,
                added_date  TEXT NOT NULL,
                notes       TEXT DEFAULT '',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 4. ETF Metadata (Sector/Geo Weights)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS etf_metadata (
                ticker      TEXT NOT NULL,
                meta_type   TEXT NOT NULL,   -- 'sector' or 'geo'
                category    TEXT NOT NULL,   -- e.g. 'Technology', 'Australia'
                weight      REAL NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, meta_type, category)
            )
        ''')
        
        # 5. ETF Holdings Attempts
        conn.execute('''
            CREATE TABLE IF NOT EXISTS etf_holdings_attempts (
                ticker       TEXT PRIMARY KEY,
                last_attempt TEXT DEFAULT CURRENT_TIMESTAMP,
                last_error   TEXT
            )
        ''')
        
        # 6. Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_etf_meta_ticker ON etf_metadata(ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_date ON watchlist(added_date)")
        
        conn.commit()
        _DB_INITIALIZED = True
        logger.info(f"Database initialised at {DB_PATH}")
    finally:
        conn.close()

def get_db_path():
    """Returns the absolute path to the database file."""
    return DB_PATH
