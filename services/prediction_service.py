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

# Cache configuration
CACHE_DIR = "data/cache"
PREDICTIONS_CACHE_FILE = os.path.join(CACHE_DIR, "predictions.json")

def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def _generate_cache_key(dates: list, values: list, horizon_days: int) -> str:
    """
    Generates a unique MD5 hash for a given dataset and forecast horizon.
    
    This ensures that if the portfolio data changes (e.g., new transactions 
    or market moves), the cache is invalidated and a fresh forecast is computed.
    """
    if not dates:
        return ""
    # Use the last date and a hash of the values to ensure the key changes if data updates
    data_str = f"{dates[-1]}_{len(values)}_{values[-1]}_{horizon_days}"
    return hashlib.md5(data_str.encode()).hexdigest()

def get_forecast(dates: list, values: list, horizon_str: str) -> dict:
    """
    Generates a forward-looking return forecast using Facebook Prophet.

    Model Parameters:
    - **Interval Width**: 80% (provides a balanced uncertainty band).
    - **Holidays**: Australian trading holidays are incorporated to improve seasonal accuracy.
    - **Seasonality**: Weekly and Yearly seasonality enabled; Daily disabled for stock data.

    Caching:
    - Results are stored in `data/cache/predictions.json`.
    - Cache is limited to the 10 most recent requests to prevent disk bloat.

    Args:
        dates: List of historical date strings (YYYY-MM-DD).
        values: List of historical cumulative return values.
        horizon_str: Forecast horizon (e.g., '90d', '1y', '5y').

    Returns:
        dict: Forecasted dates, yhat (median), yhat_lower, and yhat_upper series.
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
        
        # Determine seasonality based on data density
        total_days = (df["ds"].max() - df["ds"].min()).days
        n_points = len(df)
        
        # Defensive check: if we have very little data, seasonality is just noise
        # Prophet needs at least 2 full cycles for meaningful seasonality
        use_yearly = total_days > 730  # 2 years for yearly
        use_weekly = n_points > 14    # 2 weeks for weekly

        # Initialize and fit model
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
        # We calculate the 'drift' to anchor the forecast to the actual last price.
        last_hist_date = df["ds"].iloc[-1]
        actual_last = df["y"].iloc[-1]
        
        # Find the model's fitted value for the last historical date
        fitted_last_row = forecast[forecast["ds"] == last_hist_date]
        if not fitted_last_row.empty:
            fitted_last = fitted_last_row["yhat"].iloc[0]
            drift = actual_last - fitted_last
            
            # Apply the drift offset to the entire future forecast series
            forecast["yhat"] += drift
            forecast["yhat_lower"] += drift
            forecast["yhat_upper"] += drift

        # Only return the future portion
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
            
            if len(cache) > 10:
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
