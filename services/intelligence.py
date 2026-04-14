"""
services/intelligence.py
=========================
Pure-Python risk & allocation analytics.

All functions accept plain dicts/lists (the portfolio-store payload) and
return plain dicts so they can be called from any callback without coupling
to Dash internals.

Risk metrics
------------
  portfolio_returns(histories)      → daily return Series (portfolio-level)
  volatility(returns)               → annualised vol %
  sharpe_ratio(returns)             → Sharpe (RBA cash rate Rf)
  max_drawdown(returns)             → max peak-to-trough %
  drawdown_series(returns)          → rolling drawdown Series (for chart)
  compute_risk_metrics(port_data)   → full metrics dict

Allocation insights
-------------------
  sector_exposure(port_data)        → {sector: weight%}
  geo_exposure(port_data)           → {region: weight%}

Smart alerts
------------
  compute_smart_alerts(metrics, port_data) → list of alert dicts
"""

from __future__ import annotations

import math
import pandas as pd
import numpy as np
from datetime import datetime

# ── Risk-free rate ─────────────────────────────────────────────────────────────
# RBA cash rate target (update periodically or pull from an API)
RISK_FREE_ANNUAL = 0.0435     # 4.35 % p.a.
RISK_FREE_DAILY  = RISK_FREE_ANNUAL / 252

# ── ETF metadata ──────────────────────────────────────────────────────────────
# Sector and geography breakdown (% of ETF exposure, manually curated).
# Values are approximate blends based on fund fact sheets as of 2025.
# This serves as a fallback for known ETFs, but the system now dynamically
# handles unknown tickers from your portfolio CSV.
ETF_SECTOR: dict[str, dict[str, float]] = {
    "VHY":  {"Financials": 45, "Materials": 15, "Energy": 12,
             "Utilities": 8,  "Real Estate": 7, "Other": 13},
    "IOZ":  {"Financials": 32, "Materials": 22, "Healthcare": 10,
             "Energy": 8,     "Consumer Staples": 7, "Other": 21},
    "IOO":  {"Technology": 28, "Financials": 17, "Healthcare": 14,
             "Consumer Disc.": 11, "Industrials": 8, "Other": 22},
    "ASIA": {"Technology": 55, "Consumer Disc.": 18, "Financials": 10,
             "Communication": 9, "Other": 8},
    "SEMI": {"Technology": 95, "Industrials": 3, "Other": 2},
    "AINF": {"Utilities": 35, "Industrials": 30, "Energy": 18,
             "Real Estate": 10, "Other": 7},
}

ETF_GEO: dict[str, dict[str, float]] = {
    "VHY":  {"Australia": 100},
    "IOZ":  {"Australia": 100},
    "IOO":  {"USA": 65, "Europe": 14, "Japan": 7,  "Other": 14},
    "ASIA": {"China": 38, "Taiwan": 18, "South Korea": 13,
             "India": 12, "Other Asia": 19},
    "SEMI": {"USA": 50, "Taiwan": 15, "South Korea": 10,
             "Netherlands": 8, "Japan": 7, "Other": 10},
    "AINF": {"USA": 35, "Europe": 25, "Australia": 15,
             "Canada": 10, "Other": 15},
}


def get_unique_tickers(port_data: dict) -> list[str]:
    """
    Extract unique ticker symbols from portfolio data.
    """
    holdings = port_data.get("holdings", [])
    return list(set(h["ticker"] for h in holdings if "ticker" in h))


def get_ticker_sector_breakdown(ticker: str) -> dict[str, float]:
    """
    Get sector breakdown for a ticker. Uses hardcoded data if available,
    otherwise assigns to 'Other' category.
    """
    if ticker in ETF_SECTOR:
        return ETF_SECTOR[ticker]
    else:
        # For unknown tickers, assign 100% to "Other"
        return {"Other": 100.0}


def get_ticker_geo_breakdown(ticker: str) -> dict[str, float]:
    """
    Get geographic breakdown for a ticker. Uses hardcoded data if available,
    otherwise assigns to 'Other' category.
    """
    if ticker in ETF_GEO:
        return ETF_GEO[ticker]
    else:
        # For unknown tickers, assign 100% to "Other"
        return {"Other": 100.0}

# Alert thresholds
THRESHOLDS = {
    "sector_overweight":   40.0,   # warn if any sector > 40% of portfolio
    "geo_overweight":      60.0,   # warn if any region > 60% of portfolio
    "high_vol_annualised": 20.0,   # warn if annualised vol > 20%
    "low_sharpe":           0.5,   # warn if Sharpe < 0.5
    "bad_drawdown":        -15.0,  # warn if current drawdown worse than -15%
    "single_etf_weight":   40.0,   # warn if one ETF > 40% of portfolio
    "tech_overweight":     35.0,   # tech-specific overweight threshold
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _histories_to_returns(histories: dict) -> pd.DataFrame:
    """
    Convert the histories dict from portfolio-store into a DataFrame of
    daily returns with one column per ticker.  Dates are the index.
    """
    frames = {}
    for ticker, records in histories.items():
        df = pd.DataFrame(records)
        if df.empty or "Close" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        frames[ticker] = df["Close"].pct_change().dropna()

    if not frames:
        return pd.DataFrame()

    return pd.DataFrame(frames).dropna(how="all")


def _portfolio_weights(holdings: list[dict]) -> dict[str, float]:
    """Return {ticker: weight (0–1)} based on current market value."""
    total = sum(h["mkt_value"] for h in holdings)
    if total <= 0:
        return {}
    return {h["ticker"]: h["mkt_value"] / total for h in holdings}


# ─────────────────────────────────────────────────────────────────────────────
# Risk metrics
# ─────────────────────────────────────────────────────────────────────────────

def portfolio_returns(histories: dict, holdings: list[dict]) -> pd.Series:
    """
    Value-weighted daily portfolio return series.

    Each ticker's daily return is weighted by its portfolio weight.
    """
    ret_df  = _histories_to_returns(histories)
    weights = _portfolio_weights(holdings)

    if ret_df.empty or not weights:
        return pd.Series(dtype=float)

    # Keep only tickers present in both
    common = [t for t in weights if t in ret_df.columns]
    if not common:
        return pd.Series(dtype=float)

    w = pd.Series({t: weights[t] for t in common})
    w = w / w.sum()                          # re-normalise to 1

    port_ret = ret_df[common].mul(w, axis=1).sum(axis=1)
    return port_ret.dropna()


def annualised_volatility(returns: pd.Series) -> float:
    """Annualised volatility as a percentage."""
    if returns.empty or len(returns) < 5:
        return float("nan")
    return round(float(returns.std() * math.sqrt(252) * 100), 2)


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualised Sharpe ratio using the RBA cash rate as Rf."""
    if returns.empty or len(returns) < 5:
        return float("nan")
    excess = returns - RISK_FREE_DAILY
    if excess.std() == 0:
        return float("nan")
    return round(float(excess.mean() / excess.std() * math.sqrt(252)), 2)


def max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a percentage (negative number)."""
    if returns.empty:
        return float("nan")
    equity   = (1 + returns).cumprod()
    peak     = equity.cummax()
    drawdown = (equity - peak) / peak * 100
    return round(float(drawdown.min()), 2)


def drawdown_series(returns: pd.Series) -> pd.Series:
    """Rolling drawdown from rolling peak — used to draw the drawdown curve."""
    if returns.empty:
        return pd.Series(dtype=float)
    equity   = (1 + returns).cumprod()
    peak     = equity.cummax()
    dd       = (equity - peak) / peak * 100
    return dd.round(2)


def per_ticker_volatility(histories: dict) -> dict[str, float]:
    """Annualised volatility per ticker."""
    ret_df = _histories_to_returns(histories)
    result = {}
    for col in ret_df.columns:
        s = ret_df[col].dropna()
        result[col] = round(float(s.std() * math.sqrt(252) * 100), 2) if len(s) >= 5 else float("nan")
    return result


def compute_risk_metrics(port_data: dict) -> dict:
    """
    Top-level function: compute all risk metrics from a portfolio-store payload.

    Returns
    -------
    {
      "vol":          annualised portfolio volatility %
      "sharpe":       annualised Sharpe ratio
      "max_dd":       max drawdown %
      "current_dd":   current drawdown from all-time high %
      "ticker_vols":  {ticker: annualised vol %}
      "dd_dates":     [date strings]   ← for chart x-axis
      "dd_values":    [drawdown %]     ← for chart y-axis
      "ret_dates":    [date strings]
      "ret_values":   [cumulative return %]
      "n_days":       int
    }
    """
    empty = {
        "vol": None, "sharpe": None, "max_dd": None, "current_dd": None,
        "ticker_vols": {}, "dd_dates": [], "dd_values": [],
        "ret_dates": [], "ret_values": [], "n_days": 0,
    }

    if not port_data:
        return empty

    histories = port_data.get("histories", {})
    holdings  = port_data.get("holdings",  [])

    if not histories or not holdings:
        return empty

    port_ret = portfolio_returns(histories, holdings)
    if port_ret.empty:
        return empty

    dd_s   = drawdown_series(port_ret)
    equity = (1 + port_ret).cumprod()
    cum_ret = (equity - 1) * 100

    return {
        "vol":         annualised_volatility(port_ret),
        "sharpe":      sharpe_ratio(port_ret),
        "max_dd":      max_drawdown(port_ret),
        "current_dd":  round(float(dd_s.iloc[-1]), 2) if not dd_s.empty else None,
        "ticker_vols": per_ticker_volatility(histories),
        "dd_dates":    [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
                        for d in dd_s.index],
        "dd_values":   dd_s.tolist(),
        "ret_dates":   [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
                        for d in cum_ret.index],
        "ret_values":  cum_ret.round(2).tolist(),
        "n_days":      len(port_ret),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Allocation insights
# ─────────────────────────────────────────────────────────────────────────────

def sector_exposure(port_data: dict) -> dict[str, float]:
    """
    Portfolio-level sector exposure as % of total value.

    Each ETF's sector weights are blended by the ETF's portfolio weight.
    Uses dynamic ticker data from portfolio, with fallbacks for unknown ETFs.
    Returns {sector: weight%} sorted descending.
    """
    holdings = port_data.get("holdings", [])
    weights = _portfolio_weights(holdings)
    blended: dict[str, float] = {}

    for ticker, port_w in weights.items():
        etf_sectors = get_ticker_sector_breakdown(ticker)
        for sector, etf_pct in etf_sectors.items():
            blended[sector] = blended.get(sector, 0) + port_w * etf_pct

    # Normalise so total = 100
    total = sum(blended.values())
    if total > 0:
        blended = {k: round(v / total * 100, 1) for k, v in blended.items()}

    return dict(sorted(blended.items(), key=lambda x: x[1], reverse=True))


def geo_exposure(port_data: dict) -> dict[str, float]:
    """
    Portfolio-level geographic exposure as % of total value.
    Uses dynamic ticker data from portfolio, with fallbacks for unknown ETFs.
    """
    holdings = port_data.get("holdings", [])
    weights = _portfolio_weights(holdings)
    blended: dict[str, float] = {}

    for ticker, port_w in weights.items():
        etf_geos = get_ticker_geo_breakdown(ticker)
        for region, etf_pct in etf_geos.items():
            blended[region] = blended.get(region, 0) + port_w * etf_pct

    total = sum(blended.values())
    if total > 0:
        blended = {k: round(v / total * 100, 1) for k, v in blended.items()}

    return dict(sorted(blended.items(), key=lambda x: x[1], reverse=True))


# ─────────────────────────────────────────────────────────────────────────────
# Smart alerts
# ─────────────────────────────────────────────────────────────────────────────

def compute_smart_alerts(metrics: dict, port_data: dict) -> list[dict]:
    """
    Generate smart intelligence alerts.

    Each alert has:
      level   — "warning" | "info" | "danger"
      icon    — emoji shorthand
      title   — short headline
      detail  — one-sentence explanation
    """
    alerts: list[dict] = []
    holdings = port_data.get("holdings", [])
    if not holdings:
        return alerts

    weights     = _portfolio_weights(holdings)
    sec_exp     = sector_exposure(port_data)
    geo_exp     = geo_exposure(port_data)

    # ── Single ETF concentration ──────────────────────────────────────────────
    for ticker, w in weights.items():
        pct = round(w * 100, 1)
        if pct >= THRESHOLDS["single_etf_weight"]:
            alerts.append({
                "level":  "warning",
                "icon":   "⚖",
                "title":  f"{ticker} is {pct}% of your portfolio",
                "detail": f"A single ETF above {THRESHOLDS['single_etf_weight']:.0f}% "
                          f"concentrates risk. Consider rebalancing.",
            })

    # ── Sector overweight ─────────────────────────────────────────────────────
    for sector, pct in sec_exp.items():
        if sector == "Other":
            continue
        if pct >= THRESHOLDS["sector_overweight"]:
            alerts.append({
                "level":  "warning",
                "icon":   "🏭",
                "title":  f"Overweight {sector} ({pct}%)",
                "detail": f"More than {THRESHOLDS['sector_overweight']:.0f}% in one "
                          f"sector increases idiosyncratic risk.",
            })

    # ── Tech-specific threshold (tighter) ────────────────────────────────────
    tech_pct = sec_exp.get("Technology", 0)
    if tech_pct >= THRESHOLDS["tech_overweight"]:
        alerts.append({
            "level":  "warning",
            "icon":   "💻",
            "title":  f"High Technology exposure ({tech_pct}%)",
            "detail": "Technology is historically more volatile than the broad market.",
        })

    # ── Geographic concentration ──────────────────────────────────────────────
    for region, pct in geo_exp.items():
        if region == "Other":
            continue
        if pct >= THRESHOLDS["geo_overweight"]:
            alerts.append({
                "level":  "info",
                "icon":   "🌏",
                "title":  f"Heavy {region} exposure ({pct}%)",
                "detail": f"Over {THRESHOLDS['geo_overweight']:.0f}% in one region "
                          f"reduces geographic diversification.",
            })

    # ── Volatility ────────────────────────────────────────────────────────────
    vol = metrics.get("vol")
    if vol is not None and not math.isnan(vol):
        if vol >= THRESHOLDS["high_vol_annualised"]:
            alerts.append({
                "level":  "warning",
                "icon":   "📈",
                "title":  f"Portfolio volatility elevated ({vol:.1f}% p.a.)",
                "detail": f"Annualised volatility above {THRESHOLDS['high_vol_annualised']:.0f}% "
                          f"indicates higher short-term price swings.",
            })

    # ── Sharpe ratio ─────────────────────────────────────────────────────────
    sharpe = metrics.get("sharpe")
    if sharpe is not None and not math.isnan(sharpe):
        if sharpe < THRESHOLDS["low_sharpe"]:
            alerts.append({
                "level":  "info",
                "icon":   "📉",
                "title":  f"Low risk-adjusted return (Sharpe {sharpe:.2f})",
                "detail": "A Sharpe below 0.5 means you're taking more risk than "
                          "the return justifies vs the risk-free rate.",
            })
        elif sharpe >= 1.5:
            alerts.append({
                "level":  "info",
                "icon":   "⭐",
                "title":  f"Strong risk-adjusted return (Sharpe {sharpe:.2f})",
                "detail": "A Sharpe above 1.5 is excellent — the portfolio is "
                          "generating good returns per unit of risk.",
            })

    # ── Drawdown ──────────────────────────────────────────────────────────────
    current_dd = metrics.get("current_dd")
    if current_dd is not None and not math.isnan(current_dd):
        if current_dd <= THRESHOLDS["bad_drawdown"]:
            alerts.append({
                "level":  "danger",
                "icon":   "🔻",
                "title":  f"Portfolio in drawdown ({current_dd:.1f}%)",
                "detail": f"The portfolio is currently {abs(current_dd):.1f}% below "
                          f"its recent peak.",
            })

    # ── No alerts ─────────────────────────────────────────────────────────────
    if not alerts:
        alerts.append({
            "level":  "info",
            "icon":   "✅",
            "title":  "Portfolio looks well-balanced",
            "detail": "No concentration, volatility, or drawdown alerts at this time.",
        })

    return alerts