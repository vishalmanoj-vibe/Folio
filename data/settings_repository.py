# data/settings_repository.py
"""
data/settings_repository.py
============================
CRUD operations for the user_settings table (investor profile preferences).
"""

import logging

from data.database import get_connection

logger = logging.getLogger(__name__)

# Default profile values — used when table is empty
DEFAULTS = {
    "investment_goal": "Balanced",
    "risk_tolerance": "Moderate",
    "tax_bracket": "37%",
}


def get_all_settings() -> dict:
    """Returns all settings as a {key: value} dict, merged with defaults."""
    result = dict(DEFAULTS)
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM user_settings").fetchall()
        for row in rows:
            result[row["key"]] = row["value"]
        return result
    except Exception as e:
        logger.warning(f"Failed to load settings: {e}")
        return result
    finally:
        conn.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    """Returns a single setting value, or the default."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM user_settings WHERE key = ?", (key,)).fetchone()
        if row:
            return row["value"]
        return default or DEFAULTS.get(key)
    except Exception as e:
        logger.warning(f"Failed to get setting '{key}': {e}")
        return default or DEFAULTS.get(key)
    finally:
        conn.close()


def save_setting(key: str, value: str) -> None:
    """Upserts a single setting."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        logger.debug(f"Saved setting: {key}={value}")
    except Exception as e:
        logger.error(f"Failed to save setting '{key}': {e}")
    finally:
        conn.close()


def save_all_settings(settings: dict) -> None:
    """Upserts multiple settings in a single transaction."""
    conn = get_connection()
    try:
        for key, value in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
    finally:
        conn.close()
