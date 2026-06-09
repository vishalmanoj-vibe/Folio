import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

from services.report_service import (
    build_pdf,
    fetch_market_news,
    fetch_news_for_holdings,
    gather_report_data,
    generate_news_summaries,
    generate_weekly_report,
    get_ai_commentary,
)

# Mock data for testing
MOCK_PORTFOLIO_DATA = {
    "holdings": [
        {
            "ticker": "SEMI",
            "name": "Global X Semiconductor ETF",
            "mkt_value": 5000.0,
            "total_cost": 4500.0,
            "pnl_pct": 11.11,
            "day_chg_pct": 1.5,
            "div_yield": 0.5,
            "next_div_date": "2026-07-01",
            "payout_date": "2026-07-15",
            "last_div_amount": 0.12,
        },
        {
            "ticker": "ASIA",
            "name": "BetaShares Asia Tigers",
            "mkt_value": 3000.0,
            "total_cost": 3200.0,
            "pnl_pct": -6.25,
            "day_chg_pct": -0.8,
            "div_yield": 1.2,
        },
    ],
    "histories": {
        "SEMI": [{"Date": "2026-06-01", "Close": 10.0}, {"Date": "2026-06-02", "Close": 10.15}],
        "ASIA": [{"Date": "2026-06-01", "Close": 8.0}, {"Date": "2026-06-02", "Close": 7.94}],
    },
}


def test_gather_report_data() -> None:
    """Assert portfolio report data is gathered correctly."""
    data = gather_report_data(MOCK_PORTFOLIO_DATA)

    assert data["total_val"] == 8000.0
    assert data["total_cost"] == 7700.0
    assert round(data["pnl_pct"], 2) == 3.90
    assert data["top_performer"]["ticker"] == "SEMI"
    assert data["worst_performer"]["ticker"] == "ASIA"
    assert len(data["holdings_data"]) == 2


@patch("services.report_service.search_financial_news")
def test_fetch_news_for_holdings(mock_search: MagicMock) -> None:
    """Assert ETF news is successfully fetched and structured."""
    mock_search.return_value = [
        {"title": "SEMI jumps 5%", "href": "http://semi.com", "body": "Semiconductor news details"}
    ]

    holdings = [{"ticker": "SEMI"}, {"ticker": "ASIA"}]
    news = fetch_news_for_holdings(holdings)

    assert "SEMI" in news
    assert len(news["SEMI"]) == 1
    assert news["SEMI"][0]["title"] == "SEMI jumps 5%"
    assert news["SEMI"][0]["url"] == "http://semi.com"


@patch("services.report_service.search_financial_news")
def test_fetch_market_news(mock_search: MagicMock) -> None:
    """Assert general market news query returns structured items."""
    mock_search.return_value = [
        {"title": "ASX flat", "href": "http://asx.com", "body": "ASX news details"}
    ]

    news = fetch_market_news()
    assert len(news) > 0
    assert news[0]["title"] == "ASX flat"
    assert news[0]["url"] == "http://asx.com"


@patch("google.genai.Client")
def test_generate_news_summaries(mock_client_class: MagicMock) -> None:
    """Assert news summaries are correctly requested from Gemini and parsed."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = (
        '{"SEMI": "Semiconductors are growing.", "ASIA": "Asia tech is consolidating."}'
    )
    mock_client.models.generate_content.return_value = mock_response

    mock_news_map = {
        "SEMI": [
            {"title": "SEMI jumps", "url": "http://semi.com", "body": "Semiconductor details"}
        ],
        "ASIA": [{"title": "Asia Tech", "url": "http://asia.com", "body": "Asia tech details"}],
    }

    summaries = generate_news_summaries(mock_news_map, "dummy_api_key")

    assert "SEMI" in summaries
    assert "ASIA" in summaries
    assert summaries["SEMI"] == "Semiconductors are growing."
    assert summaries["ASIA"] == "Asia tech is consolidating."


@patch("google.genai.Client")
@patch("data.settings_repository.get_all_settings")
def test_get_ai_commentary(mock_get_settings: MagicMock, mock_client_class: MagicMock) -> None:
    """Assert AI weekly commentary prompt construction and response parsing works."""
    mock_get_settings.return_value = {
        "investment_goal": "Growth",
        "risk_tolerance": "High",
        "tax_bracket": "45%",
    }

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "This is the weekly report commentary."
    mock_client.models.generate_content.return_value = mock_response

    report_data = gather_report_data(MOCK_PORTFOLIO_DATA)
    news_map = {"SEMI": []}
    market_news = []

    commentary = get_ai_commentary(report_data, news_map, market_news, "dummy_api_key")

    assert commentary == "This is the weekly report commentary."


def test_build_pdf() -> None:
    """Assert PDF builder constructs the PDF bytes without raising exceptions."""
    report_data = gather_report_data(MOCK_PORTFOLIO_DATA)
    news_map = {
        "SEMI": [{"title": "SEMI news", "url": "http://semi.com", "body": "Semiconductors"}]
    }
    market_news = [{"title": "ASX news", "url": "http://asx.com", "body": "ASX flat"}]
    commentary = "Mock commentary"
    summaries = {"SEMI": "Semiconductor summary details."}

    pdf_bytes = build_pdf(report_data, news_map, market_news, commentary, summaries)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")


@patch("services.report_service.gather_report_data")
@patch("services.report_service.fetch_news_for_holdings")
@patch("services.report_service.fetch_market_news")
@patch("services.report_service.get_ai_commentary")
@patch("services.report_service.generate_news_summaries")
@patch("services.report_service.build_pdf")
def test_generate_weekly_report_orchestration(
    mock_build_pdf: MagicMock,
    mock_gen_summaries: MagicMock,
    mock_commentary: MagicMock,
    mock_market_news: MagicMock,
    mock_fetch_news: MagicMock,
    mock_gather_data: MagicMock,
) -> None:
    """Assert complete orchestrator logic wires all pieces together and triggers PDF build."""
    mock_gather_data.return_value = {"holdings_data": [{"ticker": "SEMI"}]}
    mock_fetch_news.return_value = {"SEMI": []}
    mock_market_news.return_value = []
    mock_commentary.return_value = "Mock commentary"
    mock_gen_summaries.return_value = {"SEMI": "Mock summary"}
    mock_build_pdf.return_value = b"PDFBYTES"

    pdf = generate_weekly_report({}, "dummy_api_key")

    assert pdf == b"PDFBYTES"
    mock_gather_data.assert_called_once()
    mock_fetch_news.assert_called_once()
    mock_market_news.assert_called_once()
    mock_commentary.assert_called_once()
    mock_gen_summaries.assert_called_once()
    mock_build_pdf.assert_called_once()
