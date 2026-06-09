import json
import os
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.research_memory import (
    append_turn,
    check_memory_size,
    cleanup_old_turns,
    ensure_memory_dir,
    load_conversation_log,
    load_memory_summary,
    run_startup_maintenance,
    save_conversation_log,
    save_memory_summary,
    summarise_old_turns,
)
from services.research_service import build_portfolio_context, get_ai_response


@pytest.fixture(autouse=True)
def mock_memory_paths(tmp_path) -> Generator[None, None, None]:
    """Isolate file reading/writing to a temporary folder during testing."""
    test_memory_dir = os.path.join(tmp_path, "research_memory")
    test_log_file = os.path.join(test_memory_dir, "conversation_log.json")
    test_summary_file = os.path.join(test_memory_dir, "memory_summary.json")

    with (
        patch("services.research_memory.MEMORY_DIR", test_memory_dir),
        patch("services.research_memory.LOG_FILE", test_log_file),
        patch("services.research_memory.SUMMARY_FILE", test_summary_file),
    ):
        yield


# ── Conversation Memory Tests (research_memory.py) ───────────────────────────


def test_ensure_memory_dir() -> None:
    """Assert memory folder is created when missing."""
    import services.research_memory as rm

    assert not os.path.exists(rm.MEMORY_DIR)
    ensure_memory_dir()
    assert os.path.exists(rm.MEMORY_DIR)


def test_conversation_log_load_save() -> None:
    """Assert conversation turns are correctly saved to and loaded from JSON files."""
    assert load_conversation_log() == []

    turns = [
        {"role": "user", "content": "VAS.AX analysis", "timestamp": "2026-05-28 12:00:00"},
        {
            "role": "assistant",
            "content": "VAS is a broad-market ETF.",
            "timestamp": "2026-05-28 12:00:05",
        },
    ]
    save_conversation_log(turns)

    loaded = load_conversation_log()
    assert len(loaded) == 2
    assert loaded[0]["role"] == "user"
    assert loaded[1]["content"] == "VAS is a broad-market ETF."


def test_memory_summary_load_save() -> None:
    """Assert weekly memory summaries are correctly stored and retrieved."""
    assert load_memory_summary() == ""

    save_memory_summary("User likes broad Australian equity ETFs like VAS and A200.")
    assert load_memory_summary() == "User likes broad Australian equity ETFs like VAS and A200."


def test_cleanup_old_turns() -> None:
    """Assert turns older than 7 days are successfully pruned from conversation logs."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_str = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")

    turns = [
        {"role": "user", "content": "Recent message", "timestamp": now_str},
        {"role": "user", "content": "Very old message", "timestamp": old_str},
        {"role": "user", "content": "Corrupt turn", "timestamp": "corrupt-date"},
    ]
    save_conversation_log(turns)

    removed = cleanup_old_turns()
    assert len(removed) == 2  # Pruned the old one and the corrupt one
    assert removed[0]["content"] == "Very old message"

    loaded = load_conversation_log()
    assert len(loaded) == 1
    assert loaded[0]["content"] == "Recent message"


@patch("google.genai.Client")
def test_summarise_old_turns(mock_client_class: MagicMock) -> None:
    """Assert Gemini API is invoked to summarise pruned turns."""
    old_turns = [
        {"role": "user", "content": "Tell me about VAS", "timestamp": "2026-05-10 12:00:00"}
    ]

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Summary: User researched VAS."
    mock_client.models.generate_content.return_value = mock_response

    summary = summarise_old_turns(old_turns, api_key="dummy_key")
    assert summary == "Summary: User researched VAS."
    mock_client.models.generate_content.assert_called_once()


@patch("services.research_memory.summarise_old_turns")
def test_run_startup_maintenance(mock_summarise: MagicMock) -> None:
    """Assert weekly maintenance prunes logs and consolidates summaries dynamically."""

    def mock_summarise_fn(old_turns, api_key, existing_summary=""):
        return f"Consolidated: {existing_summary} and new turns."

    mock_summarise.side_effect = mock_summarise_fn

    old_str = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    turns = [{"role": "user", "content": "Prune me", "timestamp": old_str}]
    save_conversation_log(turns)
    save_memory_summary("Previous summary.")

    run_startup_maintenance(api_key="dummy")

    # Assert logs pruned and summaries consolidated
    assert load_conversation_log() == []
    assert "Consolidated:" in load_memory_summary()
    assert "Previous summary." in load_memory_summary()


def test_check_memory_size_and_append() -> None:
    """Assert file sizes and capacities are parsed, and turns append ISO timestamps."""
    append_turn("user", "Adding fresh turn")

    loaded = load_conversation_log()
    assert len(loaded) == 1
    assert loaded[0]["content"] == "Adding fresh turn"
    assert "T" in loaded[0]["timestamp"]  # ISO format check

    stats = check_memory_size()
    assert "total_mb" in stats
    assert stats["total_mb"] >= 0.0
    assert stats["is_full"] is False


# ── AI Research Assistant Tests (research_service.py) ─────────────────────────


@pytest.fixture
def mock_portfolio_data() -> dict[str, Any]:
    """Fixture returning structured mock portfolio holdings and history."""
    return {
        "fetched_at": "12:00 PM",
        "holdings": [
            {
                "ticker": "VAS",
                "name": "Vanguard Australian Shares",
                "mkt_value": 10000.0,
                "div_yield": 4.2,
                "pnl_pct": 8.5,
                "last_price": 95.0,
            },
            {
                "ticker": "A200",
                "name": "BetaShares Australia 200",
                "mkt_value": 5000.0,
                "div_yield": 4.0,
                "pnl_pct": 5.0,
                "last_price": 120.0,
            },
        ],
        "histories": {
            "VAS": [{"Date": "2026-05-20", "Close": 92.0}, {"Date": "2026-05-28", "Close": 95.0}],
            "A200": [
                {"Date": "2026-05-20", "Close": 118.0},
                {"Date": "2026-05-28", "Close": 120.0},
            ],
        },
    }


def test_build_portfolio_context(mock_portfolio_data: dict[str, Any]) -> None:
    """Assert portfolio contexts are successfully structured for LLM input."""
    # Test empty fallback
    assert "not yet loaded" in build_portfolio_context({})

    # Test valid context generation
    context = build_portfolio_context(mock_portfolio_data, ticker="VAS")

    assert "PORTFOLIO SNAPSHOT" in context
    assert "VAS — Vanguard Australian Shares" in context
    assert "A200 — BetaShares Australia 200" in context
    assert "TICKER USER IS CONSIDERING BUYING: VAS" in context


@patch("services.research_service.genai")
@patch("services.research_service.should_search_web", return_value=True)
@patch(
    "services.research_service.search_financial_news",
    return_value=[{"title": "ASX VAS News", "href": "link", "body": "VAS performs well"}],
)
def test_get_ai_response_success(
    mock_search: MagicMock,
    mock_should_search: MagicMock,
    mock_genai: MagicMock,
    mock_portfolio_data: dict[str, Any],
) -> None:
    """Assert AI response parses chat histories, runs web searches, and calls Gemini."""
    history = [{"role": "user", "content": "How is VAS looking?"}]

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client

    # Setup mock Gemini Chat and response
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    mock_response = MagicMock()
    mock_response.text = (
        "VAS looks very strong based on your portfolio. Note: This is not financial advice."
    )
    mock_chat.send_message.return_value = mock_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        reply = get_ai_response(history, mock_portfolio_data, ticker="VAS")

    assert "VAS looks very strong" in reply
    mock_should_search.assert_called_once()
    mock_search.assert_called_once()
    mock_chat.send_message.assert_called_once()


@patch.dict(os.environ, {}, clear=True)
def test_get_ai_response_missing_api_key(mock_portfolio_data: dict[str, Any]) -> None:
    """Assert missing API key handles error cleanly and returns warning."""
    history = [{"role": "user", "content": "Test"}]
    reply = get_ai_response(history, mock_portfolio_data)
    assert "API key is not configured" in reply
