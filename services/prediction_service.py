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

# Cache configuration
CACHE_DIR = "data/cache"
PREDICTIONS_CACHE_FILE = os.path.join(CACHE_DIR, "predictions.json")

def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def _generate_cache_key(dates: list, values: list, horizon_days: int) -> str:
    """Generate a unique key based on the data and horizon."""
    if not dates:
        return ""
    # Use the last date and a hash of the values to ensure the key changes if data updates
    data_str = f"{dates[-1]}_{len(values)}_{values[-1]}_{horizon_days}"
    return hashlib.md5(data_str.encode()).hexdigest()

def get_forecast(dates: list, values: list, horizon_str: str) -> dict:
    """
    Get forecast data for the given horizon.
    Returns: {
        "dates": [...],
        "yhat": [...],
        "yhat_lower": [...],
        "yhat_upper": [...]
    }
    """
    horizon_map = {
        "90d": 90,
        "6m": 182,
        "1y": 365,
        "2y": 730,
        "5y": 1825
    }
    days = horizon_map.get(horizon_str, 90)
    
    if not dates or not values:
        return {}

    cache_key = _generate_cache_key(dates, values, days)
    
    # Try to load from cache
    _ensure_cache_dir()
    if os.path.exists(PREDICTIONS_CACHE_FILE):
        try:
            with open(PREDICTIONS_CACHE_FILE, "r") as f:
                cache = json.load(f)
                if cache_key in cache:
                    logger.info(f"Prediction cache hit for key {cache_key}")
                    return cache[cache_key]
        except Exception as e:
            logger.warning(f"Failed to read prediction cache: {e}")

    # Not in cache, compute it
    logger.info(f"Computing new prediction for horizon {horizon_str} ({days} days)")
    try:
        # Check if prophet is installed
        try:
            from prophet import Prophet
        except ImportError:
            logger.error("Prophet not installed. Cannot compute predictions.")
            return {}

        # Prepare data for Prophet
        df = pd.DataFrame({
            "ds": pd.to_datetime(dates),
            "y": values
        })

        # Initialize and fit model
        # Using free parameters: AU holidays, yearly/weekly seasonality.
        # Confidence interval is set to 80% (interval_width=0.80) to provide a 
        # balanced view of potential outcomes without being overly pessimistic.
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.80 
        )
        # Adding AU holidays helps the model ignore non-trading day anomalies in historical data.
        model.add_country_holidays(country_name="AU")
        model.fit(df)

        # Create future dataframe
        future = model.make_future_dataframe(periods=days, freq="D")
        
        # Remove weekends from future (optional, but cleaner for stocks)
        # Note: Financial markets are usually M-F
        # future = future[future["ds"].dt.weekday < 5]
        
        forecast = model.predict(future)

        # Only return the future portion
        last_hist_date = df["ds"].iloc[-1]
        future_mask = forecast["ds"] > last_hist_date
        res = forecast[future_mask]

        result = {
            "dates": res["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "yhat": res["yhat"].round(2).tolist(),
            "yhat_lower": res["yhat_lower"].round(2).tolist(),
            "yhat_upper": res["yhat_upper"].round(2).tolist(),
            "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # Save to cache
        try:
            cache = {}
            if os.path.exists(PREDICTIONS_CACHE_FILE):
                with open(PREDICTIONS_CACHE_FILE, "r") as f:
                    cache = json.load(f)
            
            # Limit cache size to 10 entries to avoid bloat.
            # This ensures the predictions.json file doesn't grow indefinitely 
            # while still covering the most recent ticker combinations.
            if len(cache) > 10:
                # Remove oldest entry
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
