import pandas as pd
import logging
from datetime import datetime
from services.technical_indicators import compute_rsi
from services.market.data_fetcher import extract_close

logger = logging.getLogger(__name__)

def compute_indicators(price_df: pd.DataFrame) -> dict:
    """
    Computes core indicators required for the rule-based strategy.
    Requires at least 220 days of data for reliable 200MA.
    """
    if len(price_df) < 220:
        return {"error": "Insufficient data"}
    
    # Ensure index is datetime and sorted
    price_df = price_df.sort_index()
    prices = price_df["Close"]
    
    sma_50 = prices.rolling(window=50).mean().iloc[-1]
    sma_200 = prices.rolling(window=200).mean().iloc[-1]
    rsi_series = compute_rsi(prices)
    rsi_val = float(rsi_series.iloc[-1])
    
    # Drawdown % (from 3-month high)
    # 3 months is roughly 63 trading days
    recent_high = prices.tail(63).max()
    current_price = prices.iloc[-1]
    drawdown = (recent_high - current_price) / recent_high * 100 if recent_high > 0 else 0.0
    
    return {
        "price": float(current_price),
        "sma_50": float(sma_50),
        "sma_200": float(sma_200),
        "rsi": float(rsi_val),
        "drawdown_pct": float(drawdown),
    }

def score_signal(indicators: dict, holding: dict) -> dict:
    """
    Evaluates indicators against strict thresholds to generate a signal.
    """
    if "error" in indicators:
        return {
            "signal": "HOLD",
            "score": 0.0,
            "confidence": "Low",
            "reasons": ["Insufficient data for analysis"],
            "indicators": indicators
        }
        
    score = 0.0
    reasons = []
    
    price = indicators["price"]
    sma_50 = indicators["sma_50"]
    sma_200 = indicators["sma_200"]
    rsi = indicators["rsi"]
    drawdown = indicators["drawdown_pct"]
    avg_cost = holding.get("avg_cost", price)  # Fallback to current price if missing
    
    # --- 1. Trend (0.35) ---
    trend_val = 0
    if sma_50 > sma_200:
        trend_val = 1
        score += 0.35
        reasons.append("Bullish trend (50MA > 200MA)")
    elif sma_50 < sma_200:
        trend_val = -1
        score -= 0.35
        reasons.append("Bearish trend (50MA < 200MA)")
        
    # --- 2. Momentum/RSI (0.20) ---
    if rsi < 30 and trend_val == 1:
        score += 0.20
        reasons.append(f"Oversold in bullish trend (RSI: {rsi:.1f})")
    elif rsi > 70 and trend_val == -1:
        score -= 0.20
        reasons.append(f"Overbought in bearish trend (RSI: {rsi:.1f})")
        
    # --- 3. Price vs 200MA (0.15) ---
    if price < sma_200 and trend_val == 1:
        score += 0.15
        reasons.append("Price at discount to 200MA in uptrend")
    elif price > (sma_200 * 1.1):
        score -= 0.15
        reasons.append("Price extended (>10% above 200MA)")
        
    # --- 4. Price vs Cost (0.15) ---
    if avg_cost > 0:
        if price < avg_cost and trend_val == 1:
            score += 0.15
            reasons.append("Averaging down opportunity in uptrend")
        elif price > (avg_cost * 1.2):
            score -= 0.15
            reasons.append("Significant profit margin (>20%) reached")
            
    # --- 5. Risk / Drawdown (0.15) ---
    if drawdown > 20.0:
        if trend_val == 1:
            score += 0.15
            reasons.append(f"Significant pullback in uptrend ({drawdown:.1f}%)")
        else:
            score -= 0.15
            reasons.append(f"High risk drawdown in downtrend ({drawdown:.1f}%)")
            
    # --- Final Classification ---
    confidence_val = abs(score)
    
    if score >= 0.5:
        signal = "BUY"
    elif score <= -0.5:
        signal = "SELL"
    else:
        signal = "HOLD"
        
    if abs(score) < 0.5 and len(reasons) == 0:
        reasons.append("Neutral market conditions")
        
    if confidence_val > 0.75:
        confidence_label = "High"
    elif confidence_val > 0.5:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"
        
    return {
        "signal": signal,
        "score": round(score, 3),
        "confidence": confidence_label,
        "reasons": reasons,
        "indicators": {k: round(v, 2) if isinstance(v, float) else v for k, v in indicators.items()}
    }

def generate_portfolio_signals(multi_full: pd.DataFrame, holdings: list[dict], previous_signals: dict) -> dict:
    """
    Processes all holdings through the strategy engine to generate signals.
    Applies hysteresis, logs results, and calculates CGT warnings for SELLs.
    """
    signals_output = {}
    
    for h in holdings:
        ticker = h["ticker"]
        ticker_yf = h["ticker_yf"]
        
        close_s = extract_close(multi_full, ticker_yf)
        if close_s.empty:
            signals_output[ticker] = {
                "signal": "HOLD",
                "score": 0.0,
                "confidence": "Low",
                "reasons": ["No market data found"],
                "indicators": {}
            }
            continue
            
        # Convert to DataFrame as expected by compute_indicators
        df = pd.DataFrame({"Close": close_s})
        
        # 2. Compute and Score
        inds = compute_indicators(df)
        sig_data = score_signal(inds, h)
        
        # 3. Hysteresis (Flip-prevention)
        previous = previous_signals.get(ticker)
        hysteresis_forced = False
        
        if previous and previous.get("signal"):
            prev_sig = previous["signal"]
            curr_sig = sig_data["signal"]
            curr_score = sig_data["score"]
            
            # If signals differ and new score's confidence is not overwhelmingly strong (< 0.7)
            if curr_sig != prev_sig and abs(curr_score) < 0.7:
                sig_data["signal"] = prev_sig
                sig_data["reasons"].insert(0, f"Signal held at {prev_sig} (hysteresis prevents flip)")
                hysteresis_forced = True
                
        sig_data["hysteresis_forced"] = hysteresis_forced
                
        # 4. CGT Disclaimer for SELL signals
        if sig_data["signal"] == "SELL" and "buy_tranches" in h:
            now = datetime.now()
            short_term_shares = 0
            earliest_cgt_date = None
            
            for tranche in h["buy_tranches"]:
                t_date = pd.to_datetime(tranche["date"])
                t_shares = float(tranche["shares"])
                days_held = (now - t_date).days
                
                if days_held < 365:
                    short_term_shares += t_shares
                    cgt_date = t_date + pd.DateOffset(days=365)
                    if not earliest_cgt_date or cgt_date < earliest_cgt_date:
                        earliest_cgt_date = cgt_date
                        
            if short_term_shares > 0 and earliest_cgt_date:
                cgt_str = earliest_cgt_date.strftime("%Y-%m-%d")
                warning = f"⚠️ CGT Warning: {short_term_shares} shares held < 1yr. Earliest discount eligible: {cgt_str}"
                sig_data["reasons"].append(warning)
                
        # 5. Logging
        logger.debug("[STRATEGY] %s | Score: %.2f | Signal: %s | Inds: %s", ticker, sig_data['score'], sig_data['signal'], sig_data['indicators'])
        
        signals_output[ticker] = sig_data
        
    return signals_output
