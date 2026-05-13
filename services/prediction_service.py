# services/prediction_service.py
"""
services/prediction_service.py
==============================
Handles portfolio return forecasting using Facebook Prophet.
Includes disk-based caching to ensure stability and performance.
"""

import os
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_PROPHET_AVAILABLE = None

# Cache configuration
CACHE_DIR = "data/cache"
PREDICTIONS_CACHE_FILE = os.path.join(CACHE_DIR, "predictions.json")

def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def _generate_cache_key(dates: list, horizon_str: str) -> str:
    """
    Generates a unique MD5 hash for a given dataset and forecast horizon.
    Includes the current date to ensure at least one re-computation per day.
    """
    if not dates:
        return ""
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Using first date, last date, and count for stability
    data_str = f"{dates[0]}_{dates[-1]}_{len(dates)}_{horizon_str}_{today_str}"
    return hashlib.md5(data_str.encode()).hexdigest()

def get_forecast(dates: list, values: list, horizon_str: str) -> dict:
    """
    Generates a forward-looking return forecast using Facebook Prophet.
    Optimized with stable caching, 24h staleness checks, and data downsampling.
    """
    global _PROPHET_AVAILABLE
    if _PROPHET_AVAILABLE is False:
        return {}

    # 1. Validate inputs
    if not dates or not values:
        logger.warning(f"get_forecast called with empty data: dates={len(dates)}, values={len(values)}")
        return {}

    # 2. Generate stable cache key (no prices included)
    cache_key = _generate_cache_key(dates, horizon_str)
    
    # 3. Check disk cache + Staleness check (24 hours)
    _ensure_cache_dir()
    if os.path.exists(PREDICTIONS_CACHE_FILE):
        try:
            with open(PREDICTIONS_CACHE_FILE, "r") as f:
                cache = json.load(f)
                if cache_key in cache:
                    result = cache[cache_key]
                    computed_at_str = result.get("computed_at")
                    if computed_at_str:
                        computed_at = datetime.strptime(computed_at_str, "%Y-%m-%d %H:%M")
                        # Return immediately if valid hit found within 24 hours and includes required metadata
                        if (datetime.now() - computed_at).total_seconds() < 86400 and "fitted_last" in result:
                            logger.info("Stable prediction cache hit (within 24h).")
                            return result
        except Exception as e:
            logger.warning(f"Failed to read predictions cache: {e}")

    # 4. Only after cache miss — attempt Prophet import
    if _PROPHET_AVAILABLE is None:
        try:
            from prophet import Prophet
            _PROPHET_AVAILABLE = True
        except ImportError:
            _PROPHET_AVAILABLE = False
            logger.error("Prophet not installed. return forecasting disabled.")
            return {}

    # 5. Fit and compute
    try:
        from prophet import Prophet
        horizon_map = {
            "90d": 90,
            "3mo": 90,
            "6m": 182,
            "6mo": 182,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "max": 90 # Default for max view
        }
        days = horizon_map.get(horizon_str, 90)
        
        logger.info(f"Computing new prediction for horizon {horizon_str} ({days} days)")
        
        # Prepare dataframe for Prophet
        df = pd.DataFrame({
            "ds": pd.to_datetime(dates),
            "y": values
        })
        
        # Problem 3 — Downsample to max 500 points for speed
        original_count = len(df)
        if original_count > 500:
            step = original_count // 500
            df = df.iloc[::step].copy()
            logger.info(f"Downsampled data from {original_count} to {len(df)} points for faster fitting.")
        
        # Determine seasonality based on data density (using full original length for logic)
        total_days = (df["ds"].max() - df["ds"].min()).days
        use_yearly = total_days > 730  # 2 years for yearly
        use_weekly = original_count > 14    # 2 weeks for weekly

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=use_weekly,
            yearly_seasonality=use_yearly,
            interval_width=0.80 
        )
        model.add_country_holidays(country_name="AU")
        model.fit(df)

        # Create future dataframe
        future = model.make_future_dataframe(periods=days, freq="D")
        forecast = model.predict(future)

        # ── Continuity correction ──
        # Prophet fits a global trend which may not align perfectly with the very 
        # last historical data point. This creates a vertical "jump" in the chart.
        # We return 'fitted_last' so the UI can anchor the forecast to the actual last price.
        last_hist_date = df["ds"].iloc[-1]
        fitted_last = 0.0
        
        # Find the model's fitted value for the last historical date
        fitted_last_row = forecast[forecast["ds"] == last_hist_date]
        if not fitted_last_row.empty:
            fitted_last = float(fitted_last_row["yhat"].iloc[0])
            logger.info(f"Fitted last point: {fitted_last:.2f} (actual was {df['y'].iloc[-1]:.2f})")

        # Only return the future portion
        future_mask = forecast["ds"] > last_hist_date
        res = forecast[future_mask]

        result = {
            "dates": res["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "yhat": res["yhat"].round(2).tolist(),
            "yhat_lower": res["yhat_lower"].round(2).tolist(),
            "yhat_upper": res["yhat_upper"].round(2).tolist(),
            "fitted_last": round(fitted_last, 2),
            "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # 6. Save to cache
        try:
            cache = {}
            if os.path.exists(PREDICTIONS_CACHE_FILE):
                with open(PREDICTIONS_CACHE_FILE, "r") as f:
                    cache = json.load(f)
            
            # Limited to 20 most recent requests
            if len(cache) > 20:
                oldest_key = list(cache.keys())[0]
                cache.pop(oldest_key)
                
            cache[cache_key] = result
            with open(PREDICTIONS_CACHE_FILE, "w") as f:
                json.dump(cache, f)
        except Exception as e:
            logger.warning(f"Failed to write prediction cache: {e}")

        return result

    except Exception as e:
        logger.error(f"Prediction computation failed: {e}", exc_info=True)
        return {}
