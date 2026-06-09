from unittest.mock import MagicMock, patch

import dash_mantine_components as dmc
import pytest
from dash import html

from components.header import create_header
from components.market_badge import market_badge
from components.portfolio_layout import create_layout
from components.watchlist_layout import create_watchlist_layout


def test_create_header() -> None:
    # 1. Without arguments
    header = create_header()
    assert isinstance(header, html.Div)
    assert header.className == "nav-bar"

    # 2. With market status and last updated
    status_badge = html.Span("Open")
    header_with_args = create_header(market_status=status_badge, last_updated="12:00:00")
    assert header_with_args is not None
    # Verify last updated text is set
    assert header_with_args.children[2].children[1].children[1].children == "12:00:00"


@patch("components.market_badge.is_market_open")
def test_market_badge(mock_is_open: MagicMock) -> None:
    # 1. Market open
    mock_is_open.return_value = True
    badge = market_badge()
    assert badge.children == "Open"
    assert "badge-open" in badge.className

    # 2. Market closed
    mock_is_open.return_value = False
    badge_closed = market_badge()
    assert badge_closed.children == "Closed"
    assert "badge-closed" in badge_closed.className


def test_create_layout() -> None:
    layout = create_layout()
    assert isinstance(layout, html.Div)
    assert layout.className == "page-root"


def test_create_watchlist_layout() -> None:
    layout = create_watchlist_layout()
    assert isinstance(layout, html.Div)
    assert layout.className == "page-root"
