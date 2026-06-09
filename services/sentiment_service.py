# services/sentiment_service.py
"""
services/sentiment_service.py
=============================
Retrieves and analyzes news sentiment for tickers using DDGS + Gemini.
Caches results in SQLite to limit API and scraper usage.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta

import google.genai as genai

from config.settings import GEMINI_FLASH_MODEL
from data.database import get_connection
from services.web_search import search_financial_news

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24


def get_cached_sentiment(ticker: str) -> dict | None:
    """Retrieves cached sentiment from SQLite if it exists and is not stale."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT sentiment, score, headline_1, headline_2, rationale, fetched_at
            FROM sentiment_cache
            WHERE ticker = ?
        """,
            (ticker,),
        ).fetchone()

        if row:
            fetched_at = datetime.fromisoformat(row["fetched_at"])
            is_stale = datetime.now() - fetched_at > timedelta(hours=CACHE_TTL_HOURS)
            if not is_stale:
                return {
                    "ticker": ticker,
                    "sentiment": row["sentiment"],
                    "score": row["score"],
                    "headline_1": row["headline_1"],
                    "headline_2": row["headline_2"],
                    "rationale": row["rationale"],
                    "fetched_at": row["fetched_at"],
                }
    except Exception as e:
        logger.warning(f"Failed to load cached sentiment for {ticker}: {e}")
    finally:
        conn.close()
    return None


def save_sentiment_to_cache(ticker: str, data: dict) -> None:
    """Saves analyzed sentiment to SQLite cache."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO sentiment_cache (
                ticker, sentiment, score, headline_1, headline_2, rationale, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ticker,
                data.get("sentiment", "Neutral"),
                data.get("score", 0.0),
                data.get("headline_1"),
                data.get("headline_2"),
                data.get("rationale"),
                now,
            ),
        )
        conn.commit()
        logger.debug(f"Saved sentiment to cache for {ticker}")
    except Exception as e:
        logger.error(f"Failed to save sentiment to cache for {ticker}: {e}")
    finally:
        conn.close()


def analyze_news_sentiment(ticker: str, headlines: list[dict]) -> dict:
    """Calls Gemini to analyze the sentiment of retrieved news headlines."""
    api_key = os.getenv("GEMINI_API_KEY")
    fallback = {
        "sentiment": "Neutral",
        "score": 0.0,
        "rationale": "Failed to analyze sentiment.",
    }

    if not api_key:
        logger.warning("GEMINI_API_KEY is missing. Returning neutral sentiment.")
        return fallback

    if not headlines:
        return {
            "sentiment": "Neutral",
            "score": 0.0,
            "rationale": "No recent news found for ticker.",
        }

    # Format news items for prompt
    news_text = ""
    for idx, item in enumerate(headlines[:3]):
        news_text += (
            f"Headline {idx + 1}: {item.get('title', '')}\nDescription: {item.get('body', '')}\n\n"
        )

    prompt = f"""Analyze the financial and market news sentiment for the ASX ticker '{ticker}' based on the following headlines:

{news_text}
Determine the general sentiment direction ("Positive", "Neutral", "Negative") and assign a numeric sentiment score between -1.0 (most bearish/negative) and +1.0 (most bullish/positive).

Return ONLY valid JSON in this exact structure:
{{
  "sentiment": "Positive",
  "score": 0.45,
  "rationale": "Provide a brief 1-sentence explanation of why you selected this sentiment and score."
}}
"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
            ),
        )

        # Clean markdown formatting if present
        resp_text = response.text.strip()
        match = re.search(r"\{.*\}", resp_text, re.DOTALL)
        if match:
            resp_text = match.group()

        parsed = json.loads(resp_text)
        return {
            "sentiment": parsed.get("sentiment", "Neutral"),
            "score": float(parsed.get("score", 0.0)),
            "rationale": parsed.get("rationale", "No explanation provided."),
        }
    except Exception as e:
        logger.error(f"Error calling Gemini for sentiment analysis on {ticker}: {e}")
        return fallback


def get_sentiment(ticker: str, force_refresh: bool = False) -> dict:
    """Retrieves news sentiment for a ticker (cached or live)."""
    if not force_refresh:
        cached = get_cached_sentiment(ticker)
        if cached:
            return cached

    logger.info(f"Fetching fresh sentiment for {ticker}...")

    # ASX Tickers are stored without .AX internally but news searches are more accurate with ASX context
    query = f"{ticker} ASX news"
    headlines = search_financial_news(query, max_results=3)

    h1 = headlines[0]["title"] if len(headlines) > 0 else None
    h2 = headlines[1]["title"] if len(headlines) > 1 else None

    # Call Gemini to score
    analysis = analyze_news_sentiment(ticker, headlines)

    result = {
        "ticker": ticker,
        "sentiment": analysis.get("sentiment", "Neutral"),
        "score": analysis.get("score", 0.0),
        "headline_1": h1,
        "headline_2": h2,
        "rationale": analysis.get("rationale"),
    }

    save_sentiment_to_cache(ticker, result)
    return result
