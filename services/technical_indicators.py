# services/technical_indicators.py
"""
Technical Indicators Service
============================
Provides pure-pandas implementations of common technical indicators.
Math is based on industry standards (Wilder's RSI, standard MACD 12/26/9).
No external TA libraries (pandas_ta, talib) are used to maintain portability.
"""
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute Relative Strength Index (RSI).
    Uses Wilder's smoothing method (matching industry standard).
    
    Formula:
      RSI = 100 - (100 / (1 + RS))
      RS = AvgGain / AvgLoss (smoothed using EWM with com=period-1)
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """
    Compute MACD line and Signal line.
    
    Formula:
      MACD = EMA(fast) - EMA(slow)
      Signal = EMA(MACD, signal)
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    return macd_line, signal_line

def compute_bbands(prices: pd.Series, period: int = 20, std: int = 2) -> tuple:
    """
    Compute Bollinger Bands (Upper, Middle, Lower).
    Uses 20-period SMA +/- 2 standard deviations by default.
    """
    mid = prices.rolling(period).mean()
    sd = prices.rolling(period).std()
    
    upper = mid + std * sd
    lower = mid - std * sd
    
    return upper, mid, lower

from core import get_cache, set_cache
from config.settings import TECHNICALS_CACHE_TTL

def compute_signals(ticker: str, history: list[dict] | pd.Series) -> dict:
    """
    Compute high-level technical signals from price history.
    Takes either a list of {"Date": str, "Close": float} dicts OR a pd.Series (DatetimeIndex).
    Returns a standardized dictionary of indicators and labels.
    """
    try:
        # Minimum history required for stable indicator calculation
        if history is None or len(history) < 30:
            return {"ticker": ticker, "error": "Insufficient data"}
            
        if isinstance(history, pd.Series):
            last_date = history.index[-1].strftime("%Y-%m-%d")
            prices = history
        else:
            last_date = history[-1].get("Date") or history[-1].get("date", "unknown")
            # ── Data Preparation (Fallback for legacy list format) ───────────
            df = pd.DataFrame(history)
            if "Date" not in df.columns or "Close" not in df.columns:
                return {"ticker": ticker, "error": "Missing required columns (Date/Close)"}
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            prices = df["Close"]

        cache_key = f"technicals_{ticker}_{last_date}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        
        
        if prices.empty:
            return {"ticker": ticker, "error": "Empty history"}

        # ── 2. Indicator Calculation ──────────────────────────────────────
        rsi_series = compute_rsi(prices)
        macd_line, signal_line = compute_macd(prices)
        bb_upper, bb_mid, bb_lower = compute_bbands(prices)
        
        # New indicators: SMA 200 and Volatility
        sma_200 = prices.rolling(200).mean()
        returns = prices.pct_change().dropna()
        # Annualized volatility (Std Dev of returns * sqrt of trading days)
        vol_30d = returns.tail(30).std() * (252**0.5) * 100 if len(returns) >= 30 else 0
        
        # ── 3. Signal Classification ──────────────────────────────────────
        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_line.iloc[-1])
        macd_sig = float(signal_line.iloc[-1])
        last_price = float(prices.iloc[-1])
        
        # RSI classification (Standard thresholds)
        if rsi_val < 30:
            rsi_label = "Oversold"
        elif rsi_val > 70:
            rsi_label = "Overbought"
        else:
            rsi_label = "Neutral"
            
        # MACD classification (Crossover logic)
        macd_label = "Bullish" if macd_val > macd_sig else "Bearish"
        
        # Bollinger position classification
        if last_price > bb_upper.iloc[-1]:
            bb_label = "Above upper band"
        elif last_price < bb_lower.iloc[-1]:
            bb_label = "Below lower band"
        else:
            bb_label = "Inside bands"

        # SMA 200 Trend classification
        current_sma = sma_200.iloc[-1] if not sma_200.empty else None
        if current_sma:
            sma_label = "Bullish" if last_price > current_sma else "Bearish"
        else:
            sma_label = "Insufficient Data"

        # Volatility classification
        if vol_30d == 0:
            vol_label = "Calculating..."
        elif vol_30d < 15:
            vol_label = "Low"
        elif vol_30d < 30:
            vol_label = "Medium"
        else:
            vol_label = "High"
            
        result = {
            "ticker": ticker,
            "rsi": round(rsi_val, 2),
            "rsi_label": rsi_label,
            "macd": round(macd_val, 4),
            "macd_signal": round(macd_sig, 4),
            "macd_label": macd_label,
            "bb_upper": round(bb_upper.iloc[-1], 3),
            "bb_lower": round(bb_lower.iloc[-1], 3),
            "bb_label": bb_label,
            "sma_200": round(current_sma, 3) if current_sma else None,
            "sma_label": sma_label,
            "volatility": round(vol_30d, 1),
            "vol_label": vol_label,
            "last_price": round(last_price, 3),
        }
        
        set_cache(cache_key, result, ttl=TECHNICALS_CACHE_TTL)
        return result
        
    except Exception as e:
        logger.error(f"Error computing signals for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}
