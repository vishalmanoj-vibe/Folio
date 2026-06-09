import json
import logging
import os
from datetime import datetime, timedelta

import google.genai as genai

from config.settings import DATA_CACHE_DIR, GEMINI_FLASH_MODEL

logger = logging.getLogger(__name__)

MEMORY_DIR = os.path.join(DATA_CACHE_DIR, "research_memory")
LOG_FILE = os.path.join(MEMORY_DIR, "conversation_log.json")
SUMMARY_FILE = os.path.join(MEMORY_DIR, "memory_summary.json")
MAX_FILE_SIZE_MB = 50


def ensure_memory_dir():
    """
    Creates MEMORY_DIR if it doesn't exist using os.makedirs.
    """
    os.makedirs(MEMORY_DIR, exist_ok=True)


def load_conversation_log() -> list:
    """
    Reads LOG_FILE and returns the list of conversation turns.
    Returns [] if file is missing or corrupt.
    """
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error loading conversation log: {e}")
        return []


def save_conversation_log(turns: list):
    """
    Writes the list of turns to LOG_FILE as JSON.
    """
    ensure_memory_dir()
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(turns, f, indent=4)
    except OSError as e:
        logger.error(f"Error saving conversation log: {e}")


def load_memory_summary() -> str:
    """
    Reads SUMMARY_FILE and returns the 'summary' string.
    Returns "" if file is missing or corrupt.
    """
    if not os.path.exists(SUMMARY_FILE):
        return ""
    try:
        with open(SUMMARY_FILE) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("summary", "")
            return ""
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error loading memory summary: {e}")
        return ""


def save_memory_summary(summary: str):
    """
    Writes {'summary': summary, 'updated': today's date string}
    to SUMMARY_FILE as JSON.
    """
    ensure_memory_dir()
    try:
        data = {"summary": summary, "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open(SUMMARY_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except OSError as e:
        logger.error(f"Error saving memory summary: {e}")


def cleanup_old_turns():
    """
    Loads conversation_log, keeps only turns where turn["timestamp"] is within
    the last 7 days. Saves the filtered list back and returns the removed turns.
    """
    turns = load_conversation_log()
    if not turns:
        return []

    cutoff = datetime.now() - timedelta(days=7)
    recent_turns = []
    old_turns = []

    for turn in turns:
        ts_str = turn.get("timestamp", "")
        if not ts_str:
            old_turns.append(turn)
            continue

        try:
            # Support both ISO format and legacy format
            if "T" in ts_str:
                ts = datetime.fromisoformat(ts_str)
            else:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

            if ts >= cutoff:
                recent_turns.append(turn)
            else:
                old_turns.append(turn)
        except (ValueError, TypeError):
            old_turns.append(turn)

    if old_turns:
        save_conversation_log(recent_turns)

    return old_turns


def summarise_old_turns(old_turns: list, api_key: str, existing_summary: str = "") -> str:
    """
    Summarises old turns and/or consolidates existing summaries using Gemini.
    Returns consolidated summary, or empty string on failure.
    """
    if not old_turns and not existing_summary:
        return ""

    try:
        client = genai.Client(api_key=api_key)

        # Format new turns if any
        text = ""
        if old_turns:
            for t in old_turns:
                text += f"{t['role']}: {t['content']}\n"

        if existing_summary:
            if old_turns:
                prompt = (
                    "You are an investment research assistant. You are given an existing summary of past conversations "
                    "and some new conversation turns that just occurred. Your task is to produce a single, unified, consolidated "
                    "summary (3-5 bullet points) that incorporates BOTH the historical context and the new conversation turns.\n\n"
                    "Do NOT append the summaries. Merge them into a single list of bullet points.\n\n"
                    "Focus on:\n"
                    "- Tickers discussed\n"
                    "- Conclusions reached\n"
                    "- The user's investment preferences and goals\n\n"
                    f"Existing Summary:\n{existing_summary}\n\n"
                    f"New Conversation Turns:\n{text}\n\n"
                    "Consolidated Summary (3-5 bullet points):"
                )
            else:
                # No new turns, but we need to consolidate a stacked/duplicated existing summary
                prompt = (
                    "You are an investment research assistant. You are given an existing summary of past conversations "
                    "that has accidentally had multiple summaries appended over time (causing duplicated headers and bullet points).\n"
                    "Your task is to consolidate and clean this up into a single, cohesive, unified summary (3-5 bullet points) "
                    "without any duplicate sections.\n\n"
                    f"Stacked Summary:\n{existing_summary}\n\n"
                    "Unified Consolidated Summary (3-5 bullet points):"
                )
        else:
            prompt = (
                "Summarise these investment research conversations "
                "in 3-5 bullet points. Focus on what tickers were "
                "discussed, what conclusions were reached, and what "
                "the user's investment preferences seem to be.\n\n" + text
            )

        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error summarising old turns: {e}")
        return ""


def run_startup_maintenance(api_key: str):
    """
    Runs maintenance: cleanup old turns and update summary memory.
    """
    ensure_memory_dir()
    old_turns = cleanup_old_turns()
    existing = load_memory_summary()

    # Self-healing: consolidate if there are old turns OR if the existing summary is stacked/duplicated
    has_multiple_headers = (
        existing.lower().count("summary of the") > 1
        or existing.lower().count("tickers discussed") > 1
    )

    if old_turns or has_multiple_headers:
        new_summary = summarise_old_turns(old_turns, api_key, existing_summary=existing)
        if new_summary:
            save_memory_summary(new_summary)
            logger.info("Weekly memory updated with consolidated summarised turns")


def check_memory_size() -> dict:
    """
    Checks the size of LOG_FILE and SUMMARY_FILE in MB.
    Returns a dictionary with sizes and a capacity flag.
    """
    log_size = 0
    if os.path.exists(LOG_FILE):
        log_size = os.path.getsize(LOG_FILE)

    summary_size = 0
    if os.path.exists(SUMMARY_FILE):
        summary_size = os.path.getsize(SUMMARY_FILE)

    log_mb = log_size / (1024 * 1024)
    summary_mb = summary_size / (1024 * 1024)
    total_mb = log_mb + summary_mb

    return {
        "total_mb": round(total_mb, 2),
        "is_full": total_mb >= MAX_FILE_SIZE_MB,
        "log_mb": round(log_mb, 4),
        "summary_mb": round(summary_mb, 4),
    }


def append_turn(role: str, content: str):
    """
    Appends a new turn to the conversation log with an ISO timestamp.
    Wraps operation in try/except and logs errors.
    """
    try:
        turns = load_conversation_log()
        turns.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        save_conversation_log(turns)
    except Exception as e:
        logger.error(f"Error appending turn: {e}")
