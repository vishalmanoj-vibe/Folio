"""
Chart Helpers Component.

Provides shared utilities for chart generation, such as period cutoff calculation
and benchmark trace rendering.
"""

import logging
from datetime import timedelta
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

_BENCH_STYLES = {
    "S&P 500": {"color": "#6B8FCC", "dash": "dash"},
    "ASX 200": {"color": "#CC8F6B", "dash": "dot"},
}

def _period_cutoff(period: str) -> "pd.Timestamp | None":
    """
    Calculate the start date based on a given time period string.

    Args:
        period: Time period string (e.g., "1M", "6M", "YTD", "1Y", "5Y", "max").

    Returns:
        A pandas Timestamp representing the cutoff date, or None if "max".
    """
    now = pd.Timestamp.now()
    mapping = {
        "1mo": now - timedelta(days=30),
        "3mo": now - timedelta(days=91),
        "6mo": now - timedelta(days=182),
        "1y":  now - timedelta(days=365),
        "2y":  now - timedelta(days=730),
        "max": None,
    }
    return mapping.get(period, None)

def build_benchmark_traces(period: str, portfolio_start: pd.Timestamp | None = None) -> list:
    """
    Return Plotly Scatter traces for S&P 500 and ASX 200 normalised to
    % return from the start of the selected period window or portfolio start.
    Only called when mode == 'pct'.
    """
    try:
        from services.market.data_fetcher import fetch_benchmarks
        benchmarks = fetch_benchmarks(period="max")
    except Exception as exc:
        logger.warning("Could not load benchmarks: %s", exc)
        return []

    cutoff = _period_cutoff(period)
    traces = []

    for label, records in benchmarks.items():
        if not records:
            continue
        try:
            df = pd.DataFrame(records)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

            if cutoff is not None:
                start_dt = cutoff
            elif portfolio_start is not None:
                start_dt = portfolio_start
            else:
                start_dt = None

            if start_dt is not None:
                df = df[df.index >= start_dt]

            if df.empty or len(df) < 2:
                continue

            base  = float(df["Close"].iloc[0])
            pct_s = ((df["Close"] - base) / base * 100).round(2)
            latest = float(pct_s.iloc[-1])
            sign   = "+" if latest >= 0 else ""
            style  = _BENCH_STYLES.get(label, {"color": "#888888", "dash": "dash"})

            traces.append(go.Scatter(
                x=pct_s.index.strftime("%Y-%m-%d").tolist(),
                y=pct_s.tolist(),
                name=f"{label} ({sign}{latest:.1f}%)",
                mode="lines",
                line=dict(color=style["color"], width=1.4, dash=style["dash"]),
                opacity=0.75,
                hovertemplate=f"%{{y:.2f}}%<extra>{label}</extra>",
            ))
        except Exception as exc:
            logger.warning("Benchmark trace failed for %s: %s", label, exc)

    return traces
