# Skill: Technical Analysis & Indicator Logic

## Objective
Provide robust, industry-standard technical indicators (RSI, MACD, Bollinger Bands) using pure Python and Pandas, avoiding external heavy-duty libraries like TA-Lib for better maintainability.

## Core Implementation Rules
- **Pure Pandas**: All math must be done using Pandas Series operations (`ewm`, `rolling`, `diff`, etc.).
- **Consistency**: Use standard periods (e.g., RSI 14, MACD 12/26/9) unless user-specified.
- **Robustness**: Always handle cases with insufficient history (e.g., < 30 data points) gracefully by returning an error dict.

## Indicator Specifics

### 1. Relative Strength Index (RSI)
- **Calculation**: Use Wilder's smoothing method via `ewm(com=period-1)`.
- **Classification**:
    - `< 30`: Oversold (Bullish potential)
    - `> 70`: Overbought (Bearish potential)
    - `Else`: Neutral

### 2. MACD (Moving Average Convergence Divergence)
- **Calculation**: Difference between 12-period EMA and 26-period EMA. Signal line is 9-period EMA of the MACD.
- **Classification**:
    - `MACD > Signal`: Bullish Crossover
    - `MACD < Signal`: Bearish Crossover

### 3. Bollinger Bands
- **Calculation**: 20-day Simple Moving Average (SMA) +/- 2 Standard Deviations.
- **Classification**:
    - `Price > Upper`: Above Upper Band (Overextended)
    - `Price < Lower`: Below Lower Band (Undervalued)
    - `Else`: Inside Bands

## Standard Signal Dictionary
All indicator computations should be aggregated into a standard dictionary via `compute_signals(ticker, history)`:
```python
{
    "ticker": "VHY",
    "rsi": 45.2,
    "rsi_label": "Neutral",
    "macd": 0.12,
    "macd_signal": 0.08,
    "macd_label": "Bullish",
    "bb_upper": 72.5,
    "bb_lower": 68.2,
    "bb_label": "Inside",
    "last_price": 70.4
}
```

## Integration Patterns
- **Intelligence Page**: Render as a high-density table (`intel-signals-table`).
- **Research AI**: Inject the signals as text context to help the LLM reason about market momentum.

---

## Strategy Engine (Rule-Based Signals)

### Architecture
The strategy engine (`services/strategy_engine.py`) is the single source of truth for BUY/SELL/HOLD signals. The AI analyst (`services/ai_engine.py`) only explains the engine's output — it never overrides it.

### Scoring Weights
| Dimension | Weight | Trigger |
|---|---|---|
| Trend (50MA vs 200MA) | 0.35 | Golden/Death cross |
| Momentum (RSI) | 0.20 | RSI <30 in uptrend / >70 in downtrend |
| Price vs 200MA | 0.15 | Discount in uptrend / >10% extended |
| Price vs Cost | 0.15 | Below avg cost in uptrend / >20% profit |
| Risk (Drawdown) | 0.15 | >20% pullback from 3-month high |

### Signal Boundaries
- **BUY**: `score >= 0.5`
- **SELL**: `score <= -0.5`
- **HOLD**: everything else (no dead zone between 0.2–0.5)

### Hysteresis
Prevents signal flip-flopping. If the new signal differs from the previous and `abs(new_score) < 0.7`, the old signal is held and `hysteresis_forced=True` is set on the output.

### Data Requirements
- Minimum **220 days** of OHLC history required (for reliable 200MA).
- Source: `get_full_history_cache(holdings)` — uses the same `bulk_full` key as `fetch_live`.
- Never call `yfinance` directly from the strategy engine.

### Output Shape
```python
{
  "TICKER": {
    "signal": "BUY" | "SELL" | "HOLD",
    "score": float,           # in range [-1.0, 1.0]
    "confidence": "High" | "Medium" | "Low",
    "reasons": [str, ...],    # human-readable explanations
    "indicators": {"price": float, "sma_50": float, "sma_200": float, "rsi": float, "drawdown_pct": float},
    "hysteresis_forced": bool
  }
}
```
