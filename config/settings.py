# config/settings.py
"""
Settings and configuration for Folio.

All environment variables with sensible defaults are defined here.
Easily customizable via .env file.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
import sys

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir():
    path = SCRIPT_DIR
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = get_data_dir()

DB_PATH = os.getenv("DB_PATH", os.path.join(SCRIPT_DIR, "data", "portfolio.db"))
DATA_CACHE_DIR = os.path.join(SCRIPT_DIR, "data", "cache")

# Ensure cache directory exists
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# ── Intervals ─────────────────────────────────────────────────────────────────
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_MS", 300_000))  # 5 minutes in ms
TECHNICALS_CACHE_TTL = int(os.getenv("TECHNICALS_CACHE_TTL", 86400))  # 24 hours in seconds
DIVIDENDS_CACHE_TTL = int(os.getenv("DIVIDENDS_CACHE_TTL", 604800))  # 7 days in seconds

# ── Market configuration ──────────────────────────────────────────────────────
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "Australia/Sydney")
MARKET_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
MARKET_HOURS = (10, 16)  # 10:00-16:00

# ── API retry configuration ───────────────────────────────────────────────────
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", 3))
API_RETRY_BACKOFF_BASE = float(os.getenv("API_RETRY_BACKOFF_BASE", 2.0))

# ── Cache configuration ───────────────────────────────────────────────────────
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 300))

# ── Alert thresholds ─────────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    "individual_drawdown": float(os.getenv("ALERT_INDIVIDUAL_DRAWDOWN_PCT", -20.0)),
    "portfolio_drawdown": float(os.getenv("ALERT_PORTFOLIO_DRAWDOWN_PCT", -15.0)),
}

# ── Logging configuration ─────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ── AI Model configuration ────────────────────────────────────────────────────
# Standard model: used for background batch operations and the chatbot.
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
# Enhanced model: default for manually-triggered PDF reports (higher quality).
GEMINI_REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-3.1-flash-lite")

# Default AI provider (backward compatible)
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
