import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.ai_engine import (
    _normalize_ai_response,
    _safe_parse,
    _sanitize_tone,
    analyze_signals,
)


def test_safe_parse_clean_json() -> None:
    """Assert perfect JSON parses successfully."""
    response: str = '{"VAS": {"explanation": "Ok", "risks": [], "verdict": "Reasonable"}}'
    result: dict[str, Any] = _safe_parse(response)
    assert result["VAS"]["explanation"] == "Ok"


def test_safe_parse_markdown_wrapped() -> None:
    """Assert JSON wrapped inside standard markdown brackets parses successfully."""
    response: str = '```json\n{\n  "VAS": {"explanation": "Markdown"}\n}\n```'
    result: dict[str, Any] = _safe_parse(response)
    assert result["VAS"]["explanation"] == "Markdown"


def test_safe_parse_failure() -> None:
    """Assert bad strings trigger a ValueError."""
    response: str = "This is not JSON at all."
    with pytest.raises(ValueError, match="Failed to parse AI response"):
        _safe_parse(response)


def test_sanitize_tone() -> None:
    """Assert non-neutral advisory phrases are sanitized to structural words."""
    raw_text: str = "You should buy this and sell immediately because of a strong buy."
    clean_text: str = _sanitize_tone(raw_text)

    assert "you should buy" not in clean_text.lower()
    assert "sell immediately" not in clean_text.lower()
    assert "this may indicate a positive signal" in clean_text.lower()
    assert "downside risk present" in clean_text.lower()


def test_normalize_ai_response() -> None:
    """Assert verdicts and tone are successfully normalized."""
    raw_response: dict[str, Any] = {
        "VAS": {"explanation": "You should buy", "risks": ["Strong buy"], "verdict": "Reasonable"},
        "IOZ": {"explanation": "Neutral", "risks": [], "verdict": "Conflicting"},
        "A200": {"explanation": "Fine", "risks": [], "verdict": "UnknownValue"},
    }

    normalized: dict[str, dict[str, Any]] = _normalize_ai_response(raw_response)

    assert normalized["VAS"]["verdict"] == "Confident"
    assert "positive signal" in normalized["VAS"]["explanation"]

    assert normalized["IOZ"]["verdict"] == "Risk flagged"
    assert normalized["A200"]["verdict"] == "Mixed"  # Unknown value maps to default


@patch.dict(os.environ, {}, clear=True)
def test_analyze_signals_missing_api_key() -> None:
    """Assert missing API key yields a safe default dictionary fallback."""
    mock_signals: dict[str, dict[str, Any]] = {"VAS": {"signal": "BUY", "score": 0.8}}

    result: dict[str, dict[str, Any]] = analyze_signals(mock_signals)
    assert "VAS" in result
    assert result["VAS"]["explanation"] == "API key missing"
    assert result["VAS"]["verdict"] == "Mixed"


def test_analyze_signals_low_conviction() -> None:
    """Assert signals under 0.4 absolute conviction skip Gemini entirely and return safe default."""
    mock_signals: dict[str, dict[str, Any]] = {
        "VAS": {"signal": "BUY", "score": 0.3}  # 0.3 < 0.4
    }

    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        result: dict[str, dict[str, Any]] = analyze_signals(mock_signals)

    assert "VAS" in result
    assert "low conviction" in result["VAS"]["explanation"]
    assert result["VAS"]["verdict"] == "Mixed"


@patch("services.ai_engine.get_cache")
@patch("services.ai_engine.set_cache")
@patch("google.genai.Client")
def test_analyze_signals_mocked_gemini(
    mock_client_class: MagicMock,
    mock_set_cache: MagicMock,
    mock_get_cache: MagicMock,
) -> None:
    """Assert successful high conviction API calls normalize and cache responses correctly."""
    mock_get_cache.return_value = None

    mock_signals: dict[str, dict[str, Any]] = {
        "VAS": {"signal": "BUY", "score": 0.8, "indicators": {}, "hysteresis_forced": False}
    }

    # Setup mock Gemini Response
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = (
        '{"VAS": {"explanation": "Perfect", "risks": ["Volatile"], "verdict": "Reasonable"}}'
    )
    mock_client.models.generate_content.return_value = mock_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        result: dict[str, dict[str, Any]] = analyze_signals(mock_signals)

    assert "VAS" in result
    assert result["VAS"]["explanation"] == "Perfect"
    assert result["VAS"]["verdict"] == "Confident"
    assert result["VAS"]["risks"] == ["Volatile"]
    mock_set_cache.assert_called_once()
