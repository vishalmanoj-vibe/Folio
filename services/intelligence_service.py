# services/intelligence_service.py
"""
services/intelligence_service.py
=================================
Pure-Python risk & allocation analytics.
"""

from __future__ import annotations

import csv
import logging
import math
import os
import time

import pandas as pd
import yfinance as yf

from core import get_cache, set_cache
from core.engine.utils import fmt_date_index, get_period_cutoff, normalise_tz
from services.market.data_fetcher import get_ticker_cached

logger = logging.getLogger(__name__)

# ── Risk-free rate ─────────────────────────────────────────────────────────────
RISK_FREE_ANNUAL = 0.0435
RISK_FREE_DAILY = RISK_FREE_ANNUAL / 252

# ── Alert thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "sector_overweight": 40.0,
    "geo_overweight": 60.0,
    "high_vol_annualised": 20.0,
    "low_sharpe": 0.5,
    "bad_drawdown": -15.0,
    "single_etf_weight": 40.0,
    "tech_overweight": 35.0,
}

# ── Yahoo Finance sector key → display label ──────────────────────────────────
_SECTOR_LABELS: dict[str, str] = {
    "basic-materials": "Materials",
    "basic_materials": "Materials",
    "communication-services": "Communication",
    "communication_services": "Communication",
    "consumer-cyclical": "Consumer Disc.",
    "consumer_cyclical": "Consumer Disc.",
    "consumer-defensive": "Consumer Staples",
    "consumer_defensive": "Consumer Staples",
    "energy": "Energy",
    "financial-services": "Financials",
    "financial_services": "Financials",
    "healthcare": "Healthcare",
    "industrials": "Industrials",
    "real-estate": "Real Estate",
    "real_estate": "Real Estate",
    "technology": "Technology",
    "utilities": "Utilities",
    "miscellaneous": "Miscellaneous",
    "services": "Services",
}

# ── Yahoo Finance ticker suffix → display region ──────────────────────────────
_SUFFIX_REGION: dict[str, str] = {
    "AX": "Australia",
    "XA": "Australia",
    "NZ": "New Zealand",
    "L": "United Kingdom",
    "IL": "United Kingdom",
    "PA": "France",
    "F": "Germany",
    "DE": "Germany",
    "BE": "Germany",
    "DU": "Germany",
    "MU": "Germany",
    "SG": "Germany",
    "HM": "Germany",
    "HA": "Germany",
    "AS": "Netherlands",
    "SW": "Switzerland",
    "ST": "Sweden",
    "CO": "Denmark",
    "OL": "Norway",
    "HE": "Finland",
    "LS": "Portugal",
    "MC": "Spain",
    "MI": "Italy",
    "IR": "Ireland",
    "VI": "Austria",
    "WA": "Poland",
    "PR": "Czech Rep.",
    "BU": "Hungary",
    "AT": "Greece",
    "RG": "Baltic",
    "TL": "Baltic",
    "HK": "Hong Kong",
    "SS": "China",
    "SZ": "China",
    "TW": "Taiwan",
    "TWO": "Taiwan",
    "T": "Japan",
    "KS": "South Korea",
    "KQ": "South Korea",
    "BO": "India",
    "NS": "India",
    "SI": "Singapore",
    "KL": "Malaysia",
    "JK": "Indonesia",
    "BK": "Thailand",
    "PS": "Philippines",
    "VN": "Vietnam",
    "TO": "Canada",
    "V": "Canada",
    "CN": "Canada",
    "NE": "Canada",
    "SA": "Brazil",
    "MX": "Mexico",
    "SN": "Chile",
    "CL": "Colombia",
    "TA": "Israel",
    "SR": "Saudi Arabia",
    "JO": "South Africa",
    "QA": "Qatar",
    "AE": "UAE",
}


def _symbol_to_region(symbol: str) -> str:
    s = symbol.strip()
    if "." not in s:
        return "USA"
    suffix = s.rsplit(".", 1)[1].upper()
    return _SUFFIX_REGION.get(suffix, "Other")


# ── TTL settings ──────────────────────────────────────────────────────────────
_SECTOR_TTL = 86_400
_GEO_TTL = 86_400

# ── TTL settings ──────────────────────────────────────────────────────────────
_METADATA_TTL_DAYS = 7


def _get_cached_metadata(
    ticker_yf: str, meta_type: str, ttl_days: int = _METADATA_TTL_DAYS
) -> dict[str, float] | None:
    """Retrieve metadata from SQLite with stale-check."""
    from data.database import get_connection

    ticker_yf = ticker_yf.upper()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT category, weight, updated_at
            FROM etf_metadata
            WHERE ticker = ? AND meta_type = ?
            """,
            (ticker_yf, meta_type),
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        # Check staleness (using first row's updated_at)
        updated_at = pd.to_datetime(rows[0]["updated_at"])
        age_days = (pd.Timestamp.now() - updated_at).days
        if age_days >= ttl_days:
            return None

        return {row["category"]: row["weight"] for row in rows}
    finally:
        conn.close()


def _truncate_dict(data: dict[str, float], top_n: int = 30) -> dict[str, float]:
    """Sorts a dictionary by value and keeps top N, grouping others."""
    if not data or len(data) <= top_n:
        return data
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    top_items = dict(sorted_items[:top_n])
    others_weight = sum(v for k, v in sorted_items[top_n:])
    if others_weight > 0.001:
        # Avoid double-counting if 'Other' already exists
        if "Other" in top_items:
            top_items["Other"] += others_weight
        elif "Other Holdings" in top_items:
            top_items["Other Holdings"] += others_weight
        else:
            top_items["Other Holdings"] = others_weight
    return {k: round(v, 4) for k, v in top_items.items()}


def _save_metadata(ticker_yf: str, meta_type: str, data: dict[str, float]) -> None:
    """Save metadata to SQLite. Automatically truncates holdings to Top 30."""
    from data.database import get_connection

    ticker_yf = ticker_yf.upper()

    # Surgical optimization: truncate holdings at the source
    if meta_type == "holdings":
        data = _truncate_dict(data, top_n=30)

    conn = get_connection()
    try:
        # Delete old entries for this ticker+type
        conn.execute(
            "DELETE FROM etf_metadata WHERE ticker = ? AND meta_type = ?", (ticker_yf, meta_type)
        )
        # Insert new entries
        for category, weight in data.items():
            conn.execute(
                """
                INSERT INTO etf_metadata (ticker, meta_type, category, weight, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (ticker_yf, meta_type, category, weight),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save {meta_type} metadata for {ticker_yf}: {e}")
        conn.rollback()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Live ETF metadata
# ─────────────────────────────────────────────────────────────────────────────


def fetch_etf_sector_weights(ticker_yf: str) -> dict[str, float]:
    """
    Retrieves the sector weightings for a given ETF.
    Strategy:
      1. Memory Cache (in-process)
      2. SQLite etf_metadata (7-day TTL) — populated by holdings_fetcher scrape
         (BlackRock CSV, VanEck JSON, BetaShares HTML all include sector columns)
      3. yfinance API (last resort — unreliable for many ASX ETFs)
    """
    key = f"sector_{ticker_yf}"
    cached = get_cache(key)
    if cached is not None:
        return cached

    # 1. Check SQLite Persistent Cache
    db_cached = _get_cached_metadata(ticker_yf, "sector")
    if db_cached:
        set_cache(key, db_cached, _SECTOR_TTL)
        return db_cached

    # 2. Fetch from Source (yfinance)
    try:
        tk = get_ticker_cached(ticker_yf)
        fd = getattr(tk, "funds_data", None)
        sw = fd.sector_weightings if fd is not None else None

        if not sw:
            s = tk.info.get("sector")
            result = {s: 100.0} if s else {"Unclassified": 100.0}
        else:
            labelled: dict[str, float] = {}
            other = 0.0
            for raw_key, fraction in sw.items():
                label = _SECTOR_LABELS.get(str(raw_key).lower())
                if label:
                    labelled[label] = round(float(fraction) * 100, 2)
                else:
                    other += float(fraction) * 100
            if other > 0.01:
                labelled["Other"] = round(other, 2)
            total = sum(labelled.values())
            result = (
                {k: round(v / total * 100, 2) for k, v in labelled.items()}
                if total > 0
                else {"Unclassified": 100.0}
            )

        set_cache(key, result, _SECTOR_TTL)
        _save_metadata(ticker_yf, "sector", result)
        return result
    except Exception:
        return {"Unclassified": 100.0}


def fetch_etf_geo_weights(ticker_yf: str) -> dict[str, float]:
    """
    Retrieves the geographic weightings for a given ETF.
    Strategy:
      1. Memory Cache (in-process)
      2. SQLite etf_metadata (7-day TTL) — populated by holdings_fetcher scrape
         (BlackRock CSV, VanEck JSON, BetaShares HTML all include country/location columns)
      3. yfinance API (last resort — unreliable for many ASX ETFs)
    """
    key = f"geo_{ticker_yf}"
    cached = get_cache(key)
    if cached is not None:
        return cached

    # 1. Check SQLite Persistent Cache
    db_cached = _get_cached_metadata(ticker_yf, "geo")
    if db_cached:
        set_cache(key, db_cached, _GEO_TTL)
        return db_cached

    # 2. Fetch from Source (yfinance)
    try:
        tk = get_ticker_cached(ticker_yf)
        fd = getattr(tk, "funds_data", None)
        if fd is None:
            cat = tk.info.get("category", "").lower()
            if "australia" in cat:
                result = {"Australia": 100.0}
            elif "china" in cat:
                result = {"China": 100.0}
            elif "japan" in cat:
                result = {"Japan": 100.0}
            elif "us" in cat or "america" in cat:
                result = {"USA": 100.0}
            else:
                result = {_symbol_to_region(ticker_yf): 100.0}

            set_cache(key, result, _GEO_TTL)
            _save_metadata(ticker_yf, "geo", result)
            return result

        # Regional Exposure
        try:
            re = fd.regional_exposure
            if re and isinstance(re, dict) and len(re) > 0:
                result = {k: round(float(v) * 100, 1) for k, v in re.items()}
                set_cache(key, result, _GEO_TTL)
                _save_metadata(ticker_yf, "geo", result)
                return result
        except Exception:
            pass

        # Country Exposure
        try:
            ce = fd.country_exposure
            if ce and isinstance(ce, dict) and len(ce) > 0:
                result = {k: round(float(v) * 100, 1) for k, v in ce.items()}
                set_cache(key, result, _GEO_TTL)
                _save_metadata(ticker_yf, "geo", result)
                return result
        except Exception:
            pass

        # Fallback to top_holdings
        df = fd.top_holdings
        if df is not None and not df.empty:
            region_weights: dict[str, float] = {}
            accounted = 0.0
            for symbol, row in df.iterrows():
                pct = float(row.get("Holding Percent", 0)) * 100
                if pct <= 0:
                    continue
                region = _symbol_to_region(str(symbol))
                region_weights[region] = region_weights.get(region, 0) + pct
                accounted += pct

            if accounted < 15.0:
                cat = tk.info.get("category", "").lower()
                if "australia" in cat:
                    result = {"Australia": 100.0}
                elif "china" in cat:
                    result = {"China": 100.0}
                elif "japan" in cat:
                    result = {"Japan": 100.0}
                elif "us" in cat or "america" in cat:
                    result = {"USA": 100.0}
                else:
                    result = {_symbol_to_region(ticker_yf): 100.0}
            else:
                residual = 100.0 - accounted
                if residual > 0:
                    dominant = next(
                        (r for r, w in region_weights.items() if w / accounted > 0.65), None
                    )
                    if dominant:
                        region_weights[dominant] += residual
                    else:
                        region_weights["Other"] = region_weights.get("Other", 0) + residual
                total = sum(region_weights.values())
                result = (
                    {k: round(v / total * 100, 1) for k, v in region_weights.items()}
                    if total > 0
                    else {"Unclassified": 100.0}
                )
        else:
            result = {_symbol_to_region(ticker_yf): 100.0}

        result = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        set_cache(key, result, _GEO_TTL)
        _save_metadata(ticker_yf, "geo", result)
        return result
    except Exception:
        return {"Unclassified": 100.0}


# ─────────────────────────────────────────────────────────────────────────────
# Risk & Performance logic
# ─────────────────────────────────────────────────────────────────────────────


def _histories_to_returns(histories: dict) -> pd.DataFrame:
    frames = {}
    for ticker, records in histories.items():
        df = pd.DataFrame(records)
        if df.empty or "Close" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"])
        frames[ticker] = df.set_index("Date").sort_index()["Close"].pct_change().dropna()
    return pd.DataFrame(frames).dropna(how="all") if frames else pd.DataFrame()


def _portfolio_weights(holdings: list[dict]) -> dict[str, float]:
    total = sum(h.get("mkt_value", 0) for h in holdings)
    if total <= 0:
        return {}
    return {h["ticker"]: h["mkt_value"] / total for h in holdings}


def portfolio_returns(histories: dict, holdings: list[dict]) -> pd.Series:
    ret_df = _histories_to_returns(histories)
    weights = _portfolio_weights(holdings)
    if ret_df.empty or not weights:
        return pd.Series(dtype=float)
    common = [t for t in weights if t in ret_df.columns]
    if not common:
        return pd.Series(dtype=float)
    w = pd.Series({t: weights[t] for t in common})
    w = w / w.sum()
    # We use min_count=1 to allow calculation even if some tickers are missing
    # data for certain days (e.g. newly listed or trading halt).
    # This prevents the whole backtest from disappearing.
    return ret_df[common].mul(w, axis=1).sum(axis=1, min_count=1).dropna()


def annualised_volatility(returns: pd.Series) -> float:
    """
    Computes the annualized volatility (standard deviation of returns).

    Formula: `std_dev(daily_returns) * sqrt(252) * 100`

    Args:
        returns: Pandas Series of daily fractional returns.

    Returns:
        float: Annualized volatility percentage, rounded to 2 decimal places.
    """
    if returns.empty or len(returns) < 5:
        return float("nan")
    return round(float(returns.std() * math.sqrt(252) * 100), 2)


def sharpe_ratio(returns: pd.Series) -> float:
    """
    Computes the annualized Sharpe Ratio.

    Formula: `(mean(returns) - risk_free_daily) / std_dev(returns) * sqrt(252)`

    Args:
        returns: Pandas Series of daily fractional returns.

    Returns:
        float: Annualized Sharpe Ratio, rounded to 2 decimal places.
    """
    if returns.empty or len(returns) < 5:
        return float("nan")
    excess = returns - RISK_FREE_DAILY
    if excess.std() == 0:
        return float("nan")
    return round(float(excess.mean() / excess.std() * math.sqrt(252)), 2)


def max_drawdown(returns: pd.Series) -> float:
    """
    Computes the Maximum Drawdown within the given return series.

    Drawdown is the percentage drop from the peak (all-time high)
    to the subsequent trough.

    Args:
        returns: Pandas Series of daily fractional returns.

    Returns:
        float: Maximum drawdown percentage (negative value), rounded to 2 decimal places.
    """
    if returns.empty:
        return float("nan")
    equity = (1 + returns).cumprod()
    return round(float(((equity - equity.cummax()) / equity.cummax() * 100).min()), 2)


def drawdown_series(returns: pd.Series) -> pd.Series:
    if returns.empty:
        return pd.Series(dtype=float)
    equity = (1 + returns).cumprod()
    return ((equity - equity.cummax()) / equity.cummax() * 100).round(2)


def per_ticker_volatility(histories: dict) -> dict[str, float]:
    ret_df = _histories_to_returns(histories)
    return {
        col: round(float(ret_df[col].dropna().std() * math.sqrt(252) * 100), 2)
        if len(ret_df[col].dropna()) >= 5
        else float("nan")
        for col in ret_df.columns
    }


def compute_risk_metrics(
    port_data: dict,
    period: str = "max",
    returns: pd.Series | None = None,
    histories: dict | None = None,
) -> dict:
    empty = {
        "vol": None,
        "sharpe": None,
        "max_dd": None,
        "current_dd": None,
        "ticker_vols": {},
        "dd_dates": [],
        "dd_values": [],
        "ret_dates": [],
        "ret_values": [],
        "n_days": 0,
    }
    if not port_data:
        return empty
    histories = histories or port_data.get("histories", {})
    holdings = port_data.get("holdings", [])
    if (not histories and returns is None) or not holdings:
        return empty

    port_ret = returns if returns is not None else portfolio_returns(histories, holdings)
    if port_ret.empty:
        return empty
    vol, sharpe, max_dd = (
        annualised_volatility(port_ret),
        sharpe_ratio(port_ret),
        max_drawdown(port_ret),
    )
    cur_dd = round(float(drawdown_series(port_ret).iloc[-1]), 2) if not port_ret.empty else None
    chart_ret = port_ret
    cutoff = get_period_cutoff(period)
    if cutoff is not None:
        chart_ret = port_ret[port_ret.index >= cutoff]
    if chart_ret.empty:
        return {
            "vol": vol,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "current_dd": cur_dd,
            "ticker_vols": per_ticker_volatility(histories),
            "dd_dates": [],
            "dd_values": [],
            "ret_dates": [],
            "ret_values": [],
            "n_days": len(port_ret),
        }
    dd_s, cum_ret = drawdown_series(chart_ret), ((1 + chart_ret).cumprod() - 1) * 100
    return {
        "vol": vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "current_dd": cur_dd,
        "ticker_vols": per_ticker_volatility(histories),
        "dd_dates": fmt_date_index(dd_s.index),
        "dd_values": dd_s.tolist(),
        "ret_dates": fmt_date_index(cum_ret.index),
        "ret_values": cum_ret.round(2).tolist(),
        "n_days": len(port_ret),
    }


def _get_full_exposure(port_data: dict, fetch_fn) -> dict[str, float]:
    """
    Computes the blended exposure (sector or geo) for the entire portfolio.
    """
    holdings = port_data.get("holdings", [])
    weights = _portfolio_weights(holdings)
    blended: dict[str, float] = {}

    for h in holdings:
        ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
        port_w = weights.get(h["ticker"], 0)
        if port_w <= 0:
            continue

        for category, pct in fetch_fn(ticker_yf).items():
            blended[category] = blended.get(category, 0) + port_w * pct

    total = sum(blended.values())
    return {k: round(v / total * 100, 1) for k, v in blended.items()} if total > 0 else {}


def _group_exposure(full_exp: dict[str, float]) -> dict[str, float]:
    """
    Groups small exposure categories into 'Other' to keep charts readable.
    """
    sorted_blended = sorted(full_exp.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_blended) > 15:
        top_14 = sorted_blended[:14]
        other_sum = sum(v for k, v in sorted_blended[14:])
        existing_other = next((i for i, (k, _) in enumerate(top_14) if k == "Other"), None)

        if existing_other is not None:
            top_14[existing_other] = ("Other", round(top_14[existing_other][1] + other_sum, 1))
        else:
            top_14.append(("Other", round(other_sum, 1)))
        return dict(top_14)
    return dict(sorted_blended)


def sector_exposure(port_data: dict) -> dict[str, float]:
    """Returns blended portfolio sector exposure."""
    return _group_exposure(_get_full_exposure(port_data, fetch_etf_sector_weights))


def geo_exposure(port_data: dict) -> dict[str, float]:
    """Returns blended portfolio geographic exposure."""
    return _group_exposure(_get_full_exposure(port_data, fetch_etf_geo_weights))


def get_exposure_detail(port_data: dict, exposure_type: str, category_name: str) -> list[dict]:
    """
    Returns ticker-level contributions to a specific sector or geographic category.
    Used for the sunburst chart drill-down modal.
    """
    holdings = port_data.get("holdings", [])
    weights = _portfolio_weights(holdings)
    fetch_fn = fetch_etf_sector_weights if exposure_type == "sector" else fetch_etf_geo_weights

    # Identify which categories are grouped under 'Other'
    full_exp = _get_full_exposure(port_data, fetch_fn)
    sorted_exp = sorted(full_exp.items(), key=lambda x: x[1], reverse=True)
    top_categories = (
        {k for k, v in sorted_exp[:14]} if len(sorted_exp) > 15 else {k for k, v in sorted_exp}
    )

    detail = []
    for h in holdings:
        ticker = h["ticker"]
        ticker_yf = h.get("ticker_yf", ticker + ".AX")
        port_w = weights.get(ticker, 0)
        if port_w <= 0:
            continue

        ticker_data = fetch_fn(ticker_yf)
        for cat, pct in ticker_data.items():
            contribution = port_w * pct
            if contribution <= 0:
                continue

            # Match logic: either direct category match, or if category_name is 'Other',
            # match anything not in the top 14.
            is_other_match = category_name == "Other" and cat not in top_categories
            if cat == category_name or is_other_match:
                detail.append(
                    {"ticker": ticker, "weight": round(contribution, 2), "sub_category": cat}
                )

    return sorted(detail, key=lambda x: x["weight"], reverse=True)


def compute_smart_alerts(metrics: dict, port_data: dict) -> list[dict]:
    """
    Evaluates the portfolio against predefined risk THRESHOLDS to generate alerts.

    Rules include:
    - Single ETF concentration (>40%)
    - Sector overweight (>40%)
    - High tech exposure (>35%)
    - High annualized volatility (>20%)
    - Low Sharpe ratio (<0.5)
    - Significant drawdown (<-15%)

    Args:
        metrics: Dictionary of computed risk metrics (Sharpe, Vol, etc.).
        port_data: The enriched portfolio dataset.

    Returns:
        list: A list of alert dictionaries ready for alert_card rendering.
    """
    alerts: list[dict] = []
    holdings = port_data.get("holdings", [])
    if not holdings:
        return alerts

    weights = _portfolio_weights(holdings)
    sec_exp = sector_exposure(port_data)
    geo_exp_data = geo_exposure(port_data)

    # 1. Concentration Alerts
    for ticker, w in weights.items():
        pct = round(w * 100, 1)
        if pct >= THRESHOLDS["single_etf_weight"]:
            alerts.append(
                {
                    "level": "warning",
                    "icon": "⚖",
                    "title": f"{ticker} is {pct}% of your portfolio",
                    "detail": "Concentrated risk in a single asset.",
                }
            )

    # 2. Sector Alerts
    for sector, pct in sec_exp.items():
        if sector not in ("Other", "Unclassified") and pct >= THRESHOLDS["sector_overweight"]:
            alerts.append(
                {
                    "level": "warning",
                    "icon": "🏭",
                    "title": f"Overweight {sector} ({pct}%)",
                    "detail": "Increased idiosyncratic risk from sector concentration.",
                }
            )

    tech_pct = sec_exp.get("Technology", 0)
    if THRESHOLDS["tech_overweight"] <= tech_pct < THRESHOLDS["sector_overweight"]:
        alerts.append(
            {
                "level": "info",
                "icon": "💻",
                "title": f"High Tech exposure ({tech_pct}%)",
                "detail": "Technology tends to be higher volatility.",
            }
        )

    # 3. Geography Alerts
    for region, pct in geo_exp_data.items():
        if region not in ("Other", "Unclassified") and pct >= THRESHOLDS["geo_overweight"]:
            alerts.append(
                {
                    "level": "info",
                    "icon": "🌏",
                    "title": f"Heavy {region} exposure ({pct}%)",
                    "detail": "Reduced geographic diversification.",
                }
            )

    # 4. Performance & Risk Metrics
    vol = metrics.get("vol")
    if vol is not None and not math.isnan(vol) and vol >= THRESHOLDS["high_vol_annualised"]:
        alerts.append(
            {
                "level": "warning",
                "icon": "📈",
                "title": f"Elevated Volatility ({vol:.1f}% p.a.)",
                "detail": "Expect higher-than-average price swings.",
            }
        )

    sharpe = metrics.get("sharpe")
    if sharpe is not None and not math.isnan(sharpe):
        if sharpe < THRESHOLDS["low_sharpe"]:
            alerts.append(
                {
                    "level": "info",
                    "icon": "📉",
                    "title": f"Low Sharpe Ratio ({sharpe:.2f})",
                    "detail": "Historical returns haven't fully justified the risk taken.",
                }
            )
        elif sharpe >= 1.5:
            alerts.append(
                {
                    "level": "info",
                    "icon": "⭐",
                    "title": f"Strong Sharpe Ratio ({sharpe:.2f})",
                    "detail": "Excellent risk-adjusted returns.",
                }
            )

    current_dd = metrics.get("current_dd")
    if (
        current_dd is not None
        and not math.isnan(current_dd)
        and current_dd <= THRESHOLDS["bad_drawdown"]
    ):
        alerts.append(
            {
                "level": "danger",
                "icon": "🔻",
                "title": f"Portfolio in drawdown ({current_dd:.1f}%)",
                "detail": f"Portfolio is {abs(current_dd):.1f}% below its previous all-time high.",
            }
        )

    # 5. Data Integrity Alerts
    unclassified = sec_exp.get("Unclassified", 0)
    if unclassified > 5:
        alerts.append(
            {
                "level": "info",
                "icon": "❓",
                "title": f"{unclassified:.0f}% Unclassified",
                "detail": "Missing sector data for some tickers; allocation view may be incomplete.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "level": "info",
                "icon": "✅",
                "title": "Portfolio well-balanced",
                "detail": "No significant risk alerts detected.",
            }
        )

    return alerts


def holdings_blended_data(port_data: dict) -> dict[str, dict]:
    """
    Returns aggregated ETF holdings with blended weights across the portfolio.
    Output: { "Company Name": {"weight": 2.5, "sources": {"VHY": 1.5, "IOZ": 1.0}} }
    """
    from services.market.holdings_fetcher import fetch_holdings

    holdings = port_data.get("holdings", [])
    weights = _portfolio_weights(holdings)

    blended: dict[str, dict] = {}

    for h in holdings:
        ticker = h["ticker"]
        port_w = weights.get(ticker, 0)
        if port_w <= 0:
            continue

        etf_holdings = fetch_holdings(ticker)
        if not etf_holdings:
            continue

        for company, pct in etf_holdings.items():
            contribution = (
                port_w * pct
            )  # Since pct is already a percentage (0-100) and port_w is a fraction (0-1)
            if contribution <= 0:
                continue

            if company not in blended:
                blended[company] = {"weight": 0.0, "sources": {}}

            blended[company]["weight"] += contribution
            blended[company]["sources"][ticker] = contribution

    # Rounding
    for comp in blended:
        blended[comp]["weight"] = round(blended[comp]["weight"], 2)
        for src in blended[comp]["sources"]:
            blended[comp]["sources"][src] = round(blended[comp]["sources"][src], 2)

    # Sort by weight descending
    return dict(sorted(blended.items(), key=lambda x: x[1]["weight"], reverse=True))
