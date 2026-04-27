# services/technical_indicators.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute Relative Strength Index (RSI).
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
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    return macd_line, signal_line

def compute_bbands(prices: pd.Series, period: int = 20, std: int = 2) -> tuple:
    """
    Compute Bollinger Bands (Upper, Middle, Lower).
    """
    mid = prices.rolling(period).mean()
    sd = prices.rolling(period).std()
    
    upper = mid + std * sd
    lower = mid - std * sd
    
    return upper, mid, lower

def compute_signals(ticker: str, history: list[dict]) -> dict:
    """
    Compute high-level technical signals from price history.
    Takes a list of {"Date": str, "Close": float} dicts.
    """
    try:
        if not history or len(history) < 30:
            return {"ticker": ticker, "error": "Insufficient data"}
        
        # Convert to pandas Series
        df = pd.DataFrame(history)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        prices = df["Close"]
        
        if prices.empty:
            return {"ticker": ticker, "error": "Empty history"}

        # Compute indicators
        rsi_series = compute_rsi(prices)
        macd_line, signal_line = compute_macd(prices)
        bb_upper, bb_mid, bb_lower = compute_bbands(prices)
        
        # Get latest values
        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_line.iloc[-1])
        macd_sig = float(signal_line.iloc[-1])
        last_price = float(prices.iloc[-1])
        
        # Classify RSI
        if rsi_val < 30:
            rsi_label = "Oversold"
        elif rsi_val > 70:
            rsi_label = "Overbought"
        else:
            rsi_label = "Neutral"
            
        # Classify MACD
        macd_label = "Bullish" if macd_val > macd_sig else "Bearish"
        
        # Classify Bollinger position
        if last_price > bb_upper.iloc[-1]:
            bb_label = "Above upper band"
        elif last_price < bb_lower.iloc[-1]:
            bb_label = "Below lower band"
        else:
            bb_label = "Inside bands"
            
        return {
            "ticker": ticker,
            "rsi": round(rsi_val, 2),
            "rsi_label": rsi_label,
            "macd": round(macd_val, 4),
            "macd_signal": round(macd_sig, 4),
            "macd_label": macd_label,
            "bb_upper": round(bb_upper.iloc[-1], 3),
            "bb_lower": round(bb_lower.iloc[-1], 3),
            "bb_label": bb_label,
            "last_price": round(last_price, 3),
        }
        
    except Exception as e:
        logger.error(f"Error computing signals for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}
