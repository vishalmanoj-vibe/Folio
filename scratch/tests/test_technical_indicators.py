import numpy as np
import pandas as pd
import pytest

from services.technical_indicators import (
    compute_bbands,
    compute_macd,
    compute_rsi,
    compute_signals,
)


@pytest.fixture
def sample_price_series() -> pd.Series:
    """Generates 250 days of structured mock price data for indicator stability."""
    np.random.seed(42)
    # Generate a random walk starting at $100
    steps = np.random.normal(loc=0.1, scale=1.0, size=250)
    prices = 100.0 + np.cumsum(steps)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=250, freq="D")
    return pd.Series(prices, index=dates)


def test_compute_rsi(sample_price_series):
    """Verify RSI returns a series within the standard 0-100 bounds."""
    rsi = compute_rsi(sample_price_series)
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == len(sample_price_series)
    # Ensure values in stable range (excluding the min_periods warm up)
    valid_rsi = rsi.dropna()
    assert len(valid_rsi) > 0
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_compute_macd(sample_price_series):
    """Verify MACD returns a tuple of two matched price series."""
    macd_line, signal_line = compute_macd(sample_price_series)
    assert isinstance(macd_line, pd.Series)
    assert isinstance(signal_line, pd.Series)
    assert len(macd_line) == len(sample_price_series)
    assert len(signal_line) == len(sample_price_series)


def test_compute_bbands(sample_price_series):
    """Verify Bollinger Bands returns upper, mid, lower bands matching expectation."""
    upper, mid, lower = compute_bbands(sample_price_series)
    assert isinstance(upper, pd.Series)
    assert isinstance(mid, pd.Series)
    assert isinstance(lower, pd.Series)
    # Mid band must be strictly between upper and lower bands when valid
    valid_mask = upper.notna() & mid.notna() & lower.notna()
    assert (upper[valid_mask] >= mid[valid_mask]).all()
    assert (mid[valid_mask] >= lower[valid_mask]).all()


def test_compute_signals_series(sample_price_series):
    """Verify signals computed from pd.Series yield complete dictionary outputs."""
    result = compute_signals("TEST_TICKER", sample_price_series)
    assert "error" not in result
    assert result["ticker"] == "TEST_TICKER"
    assert "rsi" in result
    assert "rsi_label" in result
    assert result["rsi_label"] in ["Neutral", "Oversold", "Overbought"]
    assert "macd_label" in result
    assert result["macd_label"] in ["Bullish", "Bearish"]
    assert "bb_label" in result
    assert result["sma_label"] in ["Bullish", "Bearish", "Insufficient Data"]
    assert "vol_label" in result


def test_compute_signals_insufficient_data():
    """Verify signals gracefully return a standard error dict on low history lengths."""
    short_series = pd.Series([10.0, 11.0, 12.0])
    result = compute_signals("SHORT_TICKER", short_series)
    assert "error" in result
    assert result["ticker"] == "SHORT_TICKER"
    assert "Insufficient data" in result["error"]
