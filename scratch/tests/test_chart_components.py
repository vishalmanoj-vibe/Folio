from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

from components.charts.helpers import (
    apply_standard_layout,
    create_empty_fig,
    hex_to_rgba,
)
from components.charts.treemap import build_portfolio_treemap


@pytest.fixture
def mock_theme_tokens() -> dict[str, Any]:
    """Strictly typed mock Plotly theme tokens."""
    return {
        "PLOTLY_BASE": {
            "font": {"color": "#ffffff", "family": "Inter"},
            "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
        },
        "T_PRI": "#ffffff",
        "T_SEC": "#aaaaaa",
        "BG": "#1c1c1a",
        "BORDER": "#333333",
        "RED": "#E24B4A",
        "WARNING": "#F39C12",
        "GREEN": "#1D9E75",
        "CYAN": "#00c9a7",
    }


@pytest.fixture
def mock_holdings() -> list[dict[str, Any]]:
    """Strictly typed mock holdings payload for chart assembly."""
    return [
        {
            "ticker": "VAS",
            "ticker_yf": "VAS.AX",
            "mkt_value": 1000.0,
            "pnl": 150.0,
            "pnl_pct": 15.0,
        },
        {
            "ticker": "VGS",
            "ticker_yf": "VGS.AX",
            "mkt_value": 2000.0,
            "pnl": -50.0,
            "pnl_pct": -2.5,
        },
    ]


def test_hex_to_rgba() -> None:
    """Assert hex conversions resolve correctly into standard CSS rgba strings."""
    assert hex_to_rgba("#00c9a7", 0.5) == "rgba(0, 201, 167, 0.5)"
    assert hex_to_rgba("333", 1.0) == "rgba(51, 51, 51, 1.0)"
    assert "rgba" in hex_to_rgba("invalid_hex", 0.8)  # Graceful exception fallback


def test_create_empty_fig(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert empty figures configure custom annotations and correct heights."""
    fig: go.Figure = create_empty_fig("Empty Test", height=350, theme_tokens=mock_theme_tokens)
    assert isinstance(fig, go.Figure)
    assert fig.layout.height == 350
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Empty Test"


def test_apply_standard_layout(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert standard layouts apply custom themes, heights, and titles safely."""
    fig = go.Figure()
    fig = apply_standard_layout(fig, mock_theme_tokens, height=400, title="Uptrend chart")
    assert fig.layout.height == 400
    assert fig.layout.title.text == "Uptrend chart"


def test_build_portfolio_treemap_empty(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert empty holdings datasets fall back gracefully to empty annotations."""
    fig: go.Figure = build_portfolio_treemap([], theme_tokens=mock_theme_tokens)
    assert isinstance(fig, go.Figure)
    assert len(fig.layout.annotations) == 1
    assert "No holdings" in fig.layout.annotations[0].text


def test_build_portfolio_treemap_flat(
    mock_holdings: list[dict[str, Any]], mock_theme_tokens: dict[str, Any]
) -> None:
    """Assert flat portfolio treemaps render correct root values and colors."""
    fig: go.Figure = build_portfolio_treemap(
        mock_holdings, theme_tokens=mock_theme_tokens, mode="flat"
    )
    assert isinstance(fig, go.Figure)

    # Assert values list matches total allocation count (2 tickers)
    data = fig.data[0]
    assert len(data.ids) == 2
    assert "VAS" in data.ids
    assert "VGS" in data.ids
    assert data.values[0] == 1000.0
    assert data.values[1] == 2000.0


def test_build_portfolio_treemap_sector(
    mock_holdings: list[dict[str, Any]], mock_theme_tokens: dict[str, Any]
) -> None:
    """Assert sector-based hierarchies construct parent sector segments correctly."""
    mock_sector_data: dict[str, dict[str, float]] = {
        "VAS": {"Financials": 60.0, "Materials": 40.0},
        "VGS": {"Technology": 100.0},
    }

    fig: go.Figure = build_portfolio_treemap(
        mock_holdings, theme_tokens=mock_theme_tokens, mode="sector", sector_data=mock_sector_data
    )
    assert isinstance(fig, go.Figure)

    data = fig.data[0]
    # Sector segments: Financials, Materials, Technology + child nodes
    assert "Financials" in data.ids
    assert "Technology" in data.ids
    assert "Financials_VAS" in data.ids


# ── P&L History Chart Tests ──────────────────────────────────────────────────


def test_build_pnl_history_figure_portfolio(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert PnL history constructs correctly in val and pct modes for a portfolio."""
    from components.charts.pnl_history import build_pnl_history_figure

    holdings_with_tranches = [
        {
            "ticker": "VAS",
            "ticker_yf": "VAS.AX",
            "total_shares": 100.0,
            "prev_close": 90.0,
            "last_price": 95.0,
            "tranches": [
                {
                    "buy_date": "2026-01-01",
                    "shares": 100.0,
                    "buy_price": 85.0,
                    "dates": ["2026-01-01", "2026-01-02", "2026-01-03"],
                    "pnl": [0.0, 500.0, 1000.0],
                }
            ],
        }
    ]

    fig_pct = build_pnl_history_figure(
        holdings_with_tranches, "pct", "1m", mock_theme_tokens, "Portfolio"
    )
    assert isinstance(fig_pct, go.Figure)

    fig_val = build_pnl_history_figure(
        holdings_with_tranches, "val", "1m", mock_theme_tokens, "Portfolio"
    )
    assert isinstance(fig_val, go.Figure)

    fig_ticker = build_pnl_history_figure(
        holdings_with_tranches, "pct", "1m", mock_theme_tokens, "VAS"
    )
    assert isinstance(fig_ticker, go.Figure)

    fig_missing = build_pnl_history_figure(
        holdings_with_tranches, "pct", "1m", mock_theme_tokens, "INVALID"
    )
    assert isinstance(fig_missing, go.Figure)


def test_build_pnl_history_figure_intraday(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert PnL history handles intraday (1d) rendering with mocked active cache sessions."""
    from unittest.mock import patch

    from components.charts.pnl_history import build_pnl_history_figure

    holdings_with_tranches = [
        {
            "ticker": "VAS",
            "ticker_yf": "VAS.AX",
            "total_shares": 100.0,
            "prev_close": 90.0,
            "last_price": 95.0,
            "tranches": [
                {
                    "buy_date": "2026-01-01",
                    "shares": 100.0,
                    "buy_price": 85.0,
                    "dates": ["2026-01-01"],
                    "pnl": [0.0],
                }
            ],
        }
    ]

    dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq="5min")
    mock_series = pd.Series([90.0 + i for i in range(10)], index=dates)

    # 1. Test successful mock data load
    with patch("data.cache_manager.get_intraday", return_value=mock_series):
        fig_1d = build_pnl_history_figure(
            holdings_with_tranches, "pct", "1d", mock_theme_tokens, "Portfolio"
        )
        assert isinstance(fig_1d, go.Figure)

    # 2. Test fallback empty state when no intraday cached
    with patch("data.cache_manager.get_intraday", return_value=pd.Series(dtype=float)):
        fig_1d_empty = build_pnl_history_figure(
            holdings_with_tranches, "pct", "1d", mock_theme_tokens, "Portfolio"
        )
        assert isinstance(fig_1d_empty, go.Figure)


# ── Dividend History Chart Tests ─────────────────────────────────────────────


def test_build_portfolio_dividend_chart(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert dividend bar charts structure months and handle empty bounds cleanly."""
    from components.charts.dividend_history import build_portfolio_dividend_chart

    # Empty case
    fig_empty = build_portfolio_dividend_chart(pd.DataFrame(), mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)

    # Non-empty case (includes item in past year and item > 1 year ago)
    dates = [
        pd.Timestamp.now() - pd.DateOffset(months=6),
        pd.Timestamp.now() - pd.DateOffset(years=2),
    ]
    df_div = pd.DataFrame({"date": dates, "total": [100.0, 50.0]})
    fig_div = build_portfolio_dividend_chart(df_div, mock_theme_tokens)
    assert isinstance(fig_div, go.Figure)


# ── Intelligence Sector exposure Tests ────────────────────────────────────────


def test_build_intel_sector_chart(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert horizontal sector bar charts handle sorting and empty fallbacks."""
    from components.charts.intel_sector import build_intel_sector_chart

    fig_empty = build_intel_sector_chart({}, mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)

    fig_sec = build_intel_sector_chart(
        {"Financials": 50.0, "Other": 10.0, "Materials": 40.0}, mock_theme_tokens
    )
    assert isinstance(fig_sec, go.Figure)


# ── Treemap Underlying Holdings Tests ─────────────────────────────────────────


def test_build_portfolio_treemap_holdings(
    mock_holdings: list[dict[str, Any]], mock_theme_tokens: dict[str, Any]
) -> None:
    """Assert underlying holdings mode builds correct hierarchical nodes and values."""
    holdings_data = {
        "VAS": {"Apple Inc.": 2.5, "Microsoft Corp.": 1.5, "Other": 96.0},
        "VGS": {"Apple Inc.": 3.0, "Microsoft Corp.": 2.5, "Other": 94.5},
    }
    # Test valid holdings mode
    fig: go.Figure = build_portfolio_treemap(
        mock_holdings,
        theme_tokens=mock_theme_tokens,
        mode="holdings",
        holdings_data=holdings_data,
    )
    assert isinstance(fig, go.Figure)
    data = fig.data[0]

    # Parents: "VAS" and "VGS" under root ""
    # Children: "VAS_Apple Inc.", "VAS_Microsoft Corp.", "VGS_Apple Inc.", "VGS_Microsoft Corp."
    assert "VAS" in data.ids
    assert "VGS" in data.ids
    assert "VAS_Apple Inc." in data.ids
    assert "VGS_Microsoft Corp." in data.ids

    # Sizing:
    # VAS total value = 1000.0. Apple Inc. weight in VAS = 2.5% -> 25.0
    # VGS total value = 2000.0. Microsoft Corp. weight in VGS = 2.5% -> 50.0
    vas_idx = data.ids.index("VAS")
    vgs_idx = data.ids.index("VGS")
    vas_apple_idx = data.ids.index("VAS_Apple Inc.")
    vgs_msft_idx = data.ids.index("VGS_Microsoft Corp.")

    assert data.values[vas_idx] == 1000.0
    assert data.values[vgs_idx] == 2000.0
    assert data.values[vas_apple_idx] == 25.0
    assert data.values[vgs_msft_idx] == 50.0

    # Test empty holdings data fallback
    fig_empty: go.Figure = build_portfolio_treemap(
        mock_holdings,
        theme_tokens=mock_theme_tokens,
        mode="holdings",
        holdings_data={},
    )
    assert isinstance(fig_empty, go.Figure)
    assert len(fig_empty.layout.annotations) == 1
    assert "No underlying holdings" in fig_empty.layout.annotations[0].text


# ── Intelligence Geographic allocation Tests ───────────────────────────────


def test_build_intel_geo_chart(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert geo allocation charts sort listings correctly."""
    from components.charts.intel_geo import build_intel_geo_chart

    fig_empty = build_intel_geo_chart({}, mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)

    fig_geo = build_intel_geo_chart(
        {"Australia": 60.0, "Other": 15.0, "United States": 25.0}, mock_theme_tokens
    )
    assert isinstance(fig_geo, go.Figure)


# ── Intelligence Performance and Drawdown Tests ──────────────────────────────


def test_build_intel_equity_chart(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert blended equity performance history generates correct trace elements."""
    from components.charts.intel_equity import build_intel_equity_chart

    fig_empty = build_intel_equity_chart([], [], mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)

    dates = ["2026-01-01", "2026-01-02"]
    vals = [5.0, 8.5]
    fig_eq = build_intel_equity_chart(dates, vals, mock_theme_tokens)
    assert isinstance(fig_eq, go.Figure)


def test_build_intel_drawdown_chart(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert drawdown charts parse min bounds and draw correct threshold lines."""
    from components.charts.intel_drawdown import build_intel_drawdown_chart

    fig_empty = build_intel_drawdown_chart([], [], mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)

    dates = ["2026-01-01", "2026-01-02"]
    vals = [-3.0, -12.5]
    fig_dd = build_intel_drawdown_chart(dates, vals, mock_theme_tokens)
    assert isinstance(fig_dd, go.Figure)


# ── Dynamic Heights helpers Tests ───────────────────────────────────────────


def test_intel_helpers() -> None:
    """Assert bar row height calculations scale layouts correctly."""
    from components.charts.intel_helpers import get_bar_height

    assert get_bar_height(1) == 200  # Enforces lower bounds
    assert get_bar_height(10) == 10 * 36 + 60


# ── Correlation Chart Tests ──────────────────────────────────────────────────


def test_build_corr_figure(mock_theme_tokens: dict[str, Any]) -> None:
    """Assert correlation heatmap figures build successfully under various inputs."""
    from components.charts.correlation import build_corr_figure

    # 1. Empty histories fallback
    fig_empty = build_corr_figure({}, "1mo", mock_theme_tokens)
    assert isinstance(fig_empty, go.Figure)
    assert len(fig_empty.layout.annotations) == 1
    assert "Need at least 2 holdings" in fig_empty.layout.annotations[0].text

    # 2. Valid histories data
    dates = pd.date_range(end="2026-06-12", periods=30, freq="D")
    histories = {
        "VAS": pd.DataFrame({"Close": [100.0 + i * 0.5 for i in range(30)], "Date": dates}),
        "VGS": pd.DataFrame({"Close": [200.0 - i * 0.3 for i in range(30)], "Date": dates}),
    }

    fig = build_corr_figure(histories, "1mo", mock_theme_tokens)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    scatter = fig.data[0]
    assert isinstance(scatter, go.Scatter)

    # Assert colorscale contains the new custom stops
    colorscale = scatter.marker.colorscale
    assert len(colorscale) == 4
    assert colorscale[0][0] == 0.0
    assert colorscale[1][0] == 0.6
    assert colorscale[2][0] == 0.75
    assert colorscale[3][0] == 1.0
