import pandas as pd
import pytest

from services.strategy_engine import (
    compute_indicators,
    generate_portfolio_signals,
    score_signal,
)


@pytest.fixture
def stable_bullish_history() -> pd.DataFrame:
    """Generates 250 business days of steady, upward-trending prices."""
    # Ensure 50MA > 200MA (Bullish trend)
    dates = pd.date_range(end="2026-05-28", periods=250, freq="B")
    prices = [100.0 + (i * 0.2) for i in range(250)]
    return pd.DataFrame({"Close": prices}, index=dates)


@pytest.fixture
def stable_bearish_history() -> pd.DataFrame:
    """Generates 250 business days of steady, downward-trending prices."""
    # Ensure 50MA < 200MA (Bearish trend)
    dates = pd.date_range(end="2026-05-28", periods=250, freq="B")
    prices = [200.0 - (i * 0.2) for i in range(250)]
    return pd.DataFrame({"Close": prices}, index=dates)


def test_compute_indicators_insufficient_data():
    """Verify compute_indicators returns an error dict if history length < 220."""
    short_df = pd.DataFrame(
        {"Close": [10.0, 11.0, 12.0]}, index=pd.date_range("2026-05-25", periods=3)
    )
    result = compute_indicators(short_df)
    assert "error" in result
    assert "Insufficient data" in result["error"]


def test_compute_indicators_success(stable_bullish_history):
    """Verify compute_indicators succeeds and generates the correct trend output."""
    result = compute_indicators(stable_bullish_history)
    assert "error" not in result
    assert result["price"] == 149.8
    assert result["sma_50"] > result["sma_200"]  # Trend must be bullish
    assert "rsi" in result
    assert "drawdown_pct" in result


def test_score_signal_buy():
    """Verify score_signal returns a BUY signal under bullish and oversold conditions."""
    indicators = {
        "price": 100.0,
        "sma_50": 110.0,  # 50MA > 200MA -> Bullish Trend (+0.35)
        "sma_200": 95.0,
        "rsi": 25.0,  # Oversold in bullish trend (+0.20)
        "drawdown_pct": 25.0,  # Pullback in uptrend (+0.15)
    }
    # Price is lower than cost basis in uptrend (+0.15)
    holding = {"avg_cost": 110.0}

    result = score_signal(indicators, holding)
    assert result["signal"] == "BUY"
    assert result["score"] >= 0.5
    assert result["confidence"] == "High"  # Score 0.85 > 0.75 is High
    assert any("Bullish trend" in r for r in result["reasons"])
    assert any("Oversold" in r for r in result["reasons"])


def test_score_signal_sell():
    """Verify score_signal returns a SELL signal under bearish or extended profit targets."""
    indicators = {
        "price": 200.0,
        "sma_50": 150.0,
        "sma_200": 170.0,  # 50MA < 200MA -> Bearish Trend (-0.35)
        "rsi": 75.0,  # Overbought in bearish trend (-0.20)
        "drawdown_pct": 25.0,  # Drawdown in downtrend (-0.15)
    }
    # Price exceeds 120% of cost basis (-0.15)
    holding = {"avg_cost": 100.0}

    result = score_signal(indicators, holding)
    assert result["signal"] == "SELL"
    assert result["score"] <= -0.5
    assert any("Bearish trend" in r for r in result["reasons"])


def test_score_signal_hold():
    """Verify neutral indicators trigger a HOLD signal."""
    indicators = {
        "price": 100.0,
        "sma_50": 100.0,
        "sma_200": 100.0,  # Trend is neutral (0.0)
        "rsi": 50.0,  # Neutral (0.0)
        "drawdown_pct": 0.0,
    }
    holding = {"avg_cost": 100.0}
    result = score_signal(indicators, holding)
    assert result["signal"] == "HOLD"
    assert result["score"] == 0.0
    assert "Neutral market conditions" in result["reasons"]


def test_generate_signals_cgt_warning(stable_bullish_history):
    """Verify a SELL signal for a young tranche appends a clear Capital Gains Tax warning."""
    # Construct a multi-index DataFrame mimicking the bulk cache
    ticker = "VAS"
    ticker_yf = "VAS.AX"

    # Force a bearish trend to guarantee a SELL signal
    dates = pd.date_range(end="2026-05-28", periods=250, freq="B")
    prices = [200.0 - (i * 0.5) for i in range(250)]
    price_df = pd.DataFrame({("Close", ticker_yf): prices}, index=dates)
    price_df.columns = pd.MultiIndex.from_tuples(price_df.columns)

    # Holding has buy tranche held for less than a year
    tranche_date = (pd.Timestamp.now() - pd.Timedelta(days=100)).strftime("%Y-%m-%d")
    holdings = [
        {
            "ticker": ticker,
            "ticker_yf": ticker_yf,
            "avg_cost": 220.0,
            "buy_tranches": [{"date": tranche_date, "shares": 100.0, "price": 220.0}],
        }
    ]

    previous_signals = {}
    signals = generate_portfolio_signals(price_df, holdings, previous_signals)

    assert ticker in signals
    assert signals[ticker]["signal"] == "SELL"
    # Verify that the CGT Warning is successfully appended to the reasons list
    reasons = signals[ticker]["reasons"]
    assert any("CGT Warning" in r for r in reasons)
    assert any("shares held < 1yr" in r for r in reasons)


def test_generate_signals_hysteresis(stable_bullish_history):
    """Verify hysteresis holds the signal to prevent flip unless score exceeds threshold."""
    ticker = "A200"
    ticker_yf = "A200.AX"

    # Steady upward trending prices
    price_df = pd.DataFrame(
        {("Close", ticker_yf): stable_bullish_history["Close"]}, index=stable_bullish_history.index
    )
    price_df.columns = pd.MultiIndex.from_tuples(price_df.columns)

    # A previous BUY signal exists
    previous_signals = {ticker: {"signal": "BUY"}}

    # Holdings have no average cost trigger
    holdings = [{"ticker": ticker, "ticker_yf": ticker_yf, "avg_cost": 0.0}]

    # Run signal generation. The new indicators will yield a score of +0.35 (trend)
    # Since +0.35 normally falls in the HOLD zone, but a previous BUY signal exists
    # and abs(+0.35) < 0.7 threshold, hysteresis should hold it to BUY.
    signals = generate_portfolio_signals(price_df, holdings, previous_signals)

    assert ticker in signals
    assert signals[ticker]["signal"] == "BUY"
    assert signals[ticker]["hysteresis_forced"] is True
    assert any("hysteresis prevents flip" in r for r in signals[ticker]["reasons"])
