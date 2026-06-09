from unittest.mock import MagicMock, patch

import dash_mantine_components as dmc
import pandas as pd
import pytest
from dash import html

from components.ui_helpers import (
    alert_card,
    chart_skeleton,
    chart_title,
    interpolate_color,
    progress_row,
    risk_card_skeleton,
    section,
    stat_card,
    stat_card_skeleton,
    table_skeleton,
    tech_signal_badges,
    txn_table,
)


def test_interpolate_color() -> None:
    # Lerp halfway between black #000000 and white #ffffff -> #7f7f7f
    res = interpolate_color("#000000", "#ffffff", 0.5)
    assert res.lower() == "#7f7f7f"

    res_start = interpolate_color("000000", "ffffff", 0.0)
    assert res_start.lower() == "#000000"

    res_end = interpolate_color("000000", "ffffff", 1.0)
    assert res_end.lower() == "#ffffff"


def test_stat_card() -> None:
    # Without tip or sub
    card = stat_card("Label", "Value")
    assert isinstance(card, html.Div)
    assert card.className == "stat-card-container"
    assert len(card.children) == 2
    assert card.children[1].children == "Value"

    # With tip and sub
    card_full = stat_card("Label", "Value", sub="Subtext", tip="Tooltip helper")
    assert len(card_full.children) == 3
    # Check that tooltip is present
    tooltip = card_full.children[0].children[1]
    assert isinstance(tooltip, dmc.Tooltip)
    assert tooltip.label == "Tooltip helper"
    assert card_full.children[2].children == "Subtext"


def test_chart_title() -> None:
    title_no_tip = chart_title("My Chart")
    assert title_no_tip.children[0].children == "My Chart"
    assert len(title_no_tip.children) == 1

    # Using valid key from config constants
    title_with_key = chart_title("My Chart", "pnl_volatility")
    assert len(title_with_key.children) == 2
    assert isinstance(title_with_key.children[1], dmc.Tooltip)


def test_section() -> None:
    title = html.H2("Title")
    content = html.P("Content")
    sec = section(title, content)
    assert sec.className == "section-container"
    assert len(sec.children) == 2

    sec_no_title = section(None, content)
    assert len(sec_no_title.children) == 1
    assert sec_no_title.children[0] == content


def test_alert_card() -> None:
    alert = {"level": "danger", "icon": "🚨", "title": "Big drop", "detail": "VAS down a lot"}
    card = alert_card(alert)
    assert card.className == "smart-alert danger"
    assert card.children[0].children == "🚨"
    assert card.children[1].children[0].children == "Big drop"


def test_txn_table() -> None:
    # Empty history
    assert isinstance(txn_table([]), html.P)
    assert txn_table([]).className == "txn-empty"

    # With items
    txns = [
        {"date": "2026-01-01", "ticker": "VAS", "type": "buy", "shares": 10.0, "price": 90.0},
        {"date": "2026-01-02", "ticker": "VGS", "type": "sell", "shares": 5.0, "price": 100.0},
    ]
    table = txn_table(txns)
    assert isinstance(table, html.Table)
    assert table.className == "table-container"
    tbody = table.children[1]
    rows = tbody.children
    assert len(rows) == 2
    # Ensure they are reversed (VGS first, then VAS)
    assert rows[0].children[1].children.children == "VGS"
    assert rows[1].children[1].children.children == "VAS"


def test_skeletons() -> None:
    assert isinstance(stat_card_skeleton(), html.Div)
    assert isinstance(risk_card_skeleton(), html.Div)
    assert isinstance(table_skeleton(3), html.Div)
    assert len(table_skeleton(3).children) == 4  # Header + 3 rows
    assert isinstance(chart_skeleton(200), html.Div)


def test_progress_row() -> None:
    row = progress_row("VAS", 50.0, 100.0, prefix="$", suffix="%")
    assert row.className == "progress-row"
    assert row.children[0].children == "VAS"
    assert "$50.00%" in row.children[2].children


@patch("services.technical_indicators.compute_signals")
def test_tech_signal_badges(mock_compute: MagicMock) -> None:
    # 1. Empty/None history
    badge_empty = tech_signal_badges("VAS", None)
    assert "Insufficient history" in badge_empty.children

    badge_empty_list = tech_signal_badges("VAS", [])
    assert "Insufficient history" in badge_empty_list.children

    # 2. Error in computing signals
    mock_compute.return_value = {"error": "Failed"}
    badge_err = tech_signal_badges("VAS", [1, 2])
    assert "Error computing technicals" in badge_err.children

    # 3. Successful compute
    mock_compute.return_value = {
        "rsi": 45.0,
        "rsi_label": "Neutral",
        "macd_label": "Bullish",
        "bb_label": "Within Bands",
        "sma_label": "Bullish",
        "vol_label": "Low",
    }
    badge_success = tech_signal_badges("VAS", [1, 2])
    assert len(badge_success.children) == 5
    # Check that tooltips are present
    assert isinstance(badge_success.children[0], dmc.Tooltip)
    assert isinstance(badge_success.children[1], dmc.Tooltip)
