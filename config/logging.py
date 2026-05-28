# config/logging.py
"""
Logging configuration for Folio.

Centralized logging with console and file handlers.
Configure via environment variables:
  - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
  - LOG_FILE: Path to log file (default: portfolio.log in script dir)
  - LOG_FILE_ENABLED: true/false to enable file logging (default: true)
"""

import logging.config
import os
import sys
from pathlib import Path

from config.settings import get_data_dir

DATA_DIR = get_data_dir()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOG_FILE = os.getenv("LOG_FILE", os.path.join(DATA_DIR, "logs", "portfolio.log"))

LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"

# Create handlers list dynamically
handlers_list = ["console"]
if LOG_FILE_ENABLED:
    handlers_list.append("file")

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)-8s] %(name)-20s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_FILE,
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 3,
            "formatter": "standard",
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "level": LOG_LEVEL,
            "handlers": handlers_list,
            "propagate": True,
        },
        # Suppress noisy third-party loggers
        "yfinance": {
            "level": "WARNING",
        },
        "urllib3": {
            "level": "WARNING",
        },
        "dash": {
            "level": "INFO",
        },
    },
}


def setup_logging():
    """Initialize logging configuration."""
    # Ensure log directory exists
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig(CONFIG)
    logger = logging.getLogger(__name__)

    if LOG_FILE_ENABLED:
        logger.info(f"Logging configured: console={LOG_LEVEL}, file={LOG_FILE}")
    else:
        logger.info(f"Logging configured: console={LOG_LEVEL} (file logging disabled)")
