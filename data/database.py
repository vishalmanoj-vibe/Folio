# data/database.py
import sqlite3
import os
import logging
from config.settings import CSV_PATH

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(CSV_PATH), "portfolio.db"
)

def get_connection():
    """Opens and returns a sqlite3 connection to DB_PATH with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the transactions table if it does not exist and logs the action."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
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
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialised at {DB_PATH}")

def get_db_path():
    """Returns the absolute path to the database file."""
    return DB_PATH
