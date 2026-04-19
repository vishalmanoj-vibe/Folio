"""
services/intelligence_service.py
=================================
Pure-Python risk & allocation analytics.

Geographic exposure fix
-----------------------
Previous version called yf.Ticker(symbol).fast_info and tried
getattr(info, "country") — but FastInfo has NO country attribute.
It only holds price/volume fields.

Fixed approach: parse the Yahoo Finance exchange suffix from the
holding symbol itself (e.g. "0700.HK" → Hong Kong, "AAPL" → USA,
"CBA.AX" → Australia). This requires zero extra API calls and works
for every symbol that appears in funds_data.top_holdings.

Sector exposure
---------------
Uses yf.Ticker.funds_data.sector_weightings — already correct,
just needed the label mapping verified.

Both are cached 24 h in-process.
"""

from __future__ import annotations
import math
import time
import logging
import csv
import os
import pandas as pd
import yfinance as yf

from config.settings import METADATA_CSV_PATH
from core.engine.utils import get_period_cutoff, normalise_tz, fmt_date_index
from services.market.data_fetcher import get_ticker_cached

logger = logging.getLogger(__name__)

# ── Risk-free rate ─────────────────────────────────────────────────────────────
RISK_FREE_ANNUAL = 0.0435
RISK_FREE_DAILY  = RISK_FREE_ANNUAL / 252

# ── Alert thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "sector_overweight":   40.0,
    "geo_overweight":      60.0,
    "high_vol_annualised": 20.0,
    "low_sharpe":           0.5,
    "bad_drawdown":        -15.0,
    "single_etf_weight":   40.0,
    "tech_overweight":     35.0,
}

# ── Yahoo Finance sector key → display label ──────────────────────────────────
_SECTOR_LABELS: dict[str, str] = {
    "basic-materials":        "Materials",
    "communication-services": "Communication",
    "consumer-cyclical":      "Consumer Disc.",
    "consumer-defensive":     "Consumer Staples",
    "energy":                 "Energy",
    "financial-services":     "Financials",
    "healthcare":             "Healthcare",
    "industrials":            "Industrials",
    "real-estate":            "Real Estate",
    "technology":             "Technology",
    "utilities":              "Utilities",
}

# ── Yahoo Finance ticker suffix → display region ──────────────────────────────
# Symbol format: "AAPL" (no suffix = US), "CBA.AX", "0700.HK", "2330.TW"
# Suffixes come directly from funds_data.top_holdings index — no API call needed.
_SUFFIX_REGION: dict[str, str] = {
    # Australia / NZ
    "AX": "Australia",   "XA": "Australia",   "NZ": "New Zealand",
    # UK
    "L":  "United Kingdom",  "IL": "United Kingdom",
    # Europe
    "PA": "France",      "F":  "Germany",      "DE": "Germany",
    "BE": "Germany",     "DU": "Germany",      "MU": "Germany",
    "SG": "Germany",     "HM": "Germany",      "HA": "Germany",
    "AS": "Netherlands", "SW": "Switzerland",  "ST": "Sweden",
    "CO": "Denmark",     "OL": "Norway",       "HE": "Finland",
    "LS": "Portugal",    "MC": "Spain",        "MI": "Italy",
    "IR": "Ireland",     "VI": "Austria",      "WA": "Poland",
    "PR": "Czech Rep.",  "BU": "Hungary",      "AT": "Greece",
    "RG": "Baltic",      "TL": "Baltic",
    # Asia-Pacific
    "HK": "Hong Kong",   "SS": "China",        "SZ": "China",
    "TW": "Taiwan",      "TWO": "Taiwan",
    "T":  "Japan",       "KS": "South Korea",  "KQ": "South Korea",
    "BO": "India",       "NS": "India",
    "SI": "Singapore",   "KL": "Malaysia",
    "JK": "Indonesia",   "BK": "Thailand",
    "PS": "Philippines", "VN": "Vietnam",
    # Americas
    "TO": "Canada",      "V":  "Canada",       "CN": "Canada",
    "NE": "Canada",
    "SA": "Brazil",      "MX": "Mexico",       "SN": "Chile",
    "CL": "Colombia",
    # Middle East & Africa
    "TA": "Israel",      "SR": "Saudi Arabia",
    "JO": "South Africa","QA": "Qatar",        "AE": "UAE",
}


def _symbol_to_region(symbol: str) -> str:
    """
    Infer geographic region from a Yahoo Finance ticker symbol.

    Logic:
      - No "." in symbol  →  NYSE / NASDAQ  →  "USA"
      - Has suffix        →  look up in _SUFFIX_REGION
      - Unknown suffix    →  "Other"
    """
    s = symbol.strip()
    if "." not in s:
        return "USA"
    suffix = s.rsplit(".", 1)[1].upper()
    return _SUFFIX_REGION.get(suffix, "Other")


# No-longer needed local _get_period_cutoff


# ── In-process TTL cache ──────────────────────────────────────────────────────
_INTEL_CACHE: dict[str, tuple] = {}
_SECTOR_TTL = 86_400   # 24 h — sector weights barely change
_GEO_TTL    = 86_400


def _cache_get(key: str):
    entry = _INTEL_CACHE.get(key)
    if not entry:
        return None
    value, expiry = entry
    if time.time() > expiry:
        del _INTEL_CACHE[key]
        return None
    return value


def _cache_set(key: str, value, ttl: int) -> None:
    _INTEL_CACHE[key] = (value, time.time() + ttl)


# ── CSV Persistent Cache ──────────────────────────────────────────────────────
_CSV_CACHE_STORE: dict[str, dict] = {}
_CSV_LOADED = False

def _load_metadata_csv():
    global _CSV_LOADED, _CSV_CACHE_STORE
    if _CSV_LOADED:
        return
    _CSV_LOADED = True
    if not os.path.exists(METADATA_CSV_PATH):
        return
    try:
        df = pd.read_csv(METADATA_CSV_PATH)
        for (ticker, meta_type), group in df.groupby(["ticker", "type"]):
            key = f"{meta_type}_{ticker}"
            _CSV_CACHE_STORE[key] = dict(zip(group["category"], group["weight"]))
        logger.info(f"Loaded ETF metadata cache from {METADATA_CSV_PATH}")
    except Exception as exc:
        logger.error(f"Failed to load metadata CSV: {exc}")

def _append_metadata_csv(ticker: str, meta_type: str, data: dict):
    file_exists = os.path.exists(METADATA_CSV_PATH)
    try:
        os.makedirs(os.path.dirname(METADATA_CSV_PATH), exist_ok=True)
        with open(METADATA_CSV_PATH, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["ticker", "type", "category", "weight"])
            for k, v in data.items():
                writer.writerow([ticker, meta_type, k, v])
    except Exception as exc:
        logger.error(f"Failed to append to metadata CSV: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Live ETF metadata
# ─────────────────────────────────────────────────────────────────────────────

def fetch_etf_sector_weights(ticker_yf: str) -> dict[str, float]:
    """
    Fetch sector weightings from yfinance funds_data.sector_weightings.

    Returns {display_label: pct%} normalised to 100.
    Cached 24 h. Returns {"Unclassified": 100.0} on failure.
    """
    key = f"sector_{ticker_yf}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    _load_metadata_csv()
    if key in _CSV_CACHE_STORE:
        result = _CSV_CACHE_STORE[key]
        _cache_set(key, result, _SECTOR_TTL)
        return result

    try:
        tk = get_ticker_cached(ticker_yf)
        sw = tk.funds_data.sector_weightings  # {yf_key: 0-1 float}

        if not sw:
            result = {"Unclassified": 100.0}
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
            result = {k: round(v / total * 100, 2) for k, v in labelled.items()} \
                     if total > 0 else {"Unclassified": 100.0}

        _cache_set(key, result, _SECTOR_TTL)
        _CSV_CACHE_STORE[key] = result
        _append_metadata_csv(ticker_yf, "sector", result)
        logger.debug("Sector %s: %s", ticker_yf, result)
        return result

    except Exception as exc:
        logger.warning("Sector fetch failed %s: %s", ticker_yf, exc)
        result = {"Unclassified": 100.0}
        _cache_set(key, result, 300)   # short TTL → retry sooner
        return result


def fetch_etf_geo_weights(ticker_yf: str) -> dict[str, float]:
    """
    Infer geographic exposure from top holdings symbols.

    Strategy (no extra API calls per holding):
      1. Fetch top_holdings DataFrame (symbol → holding_percent)
         from funds_data — already part of the same API call used
         by sector weights.
      2. Parse the exchange suffix from each symbol string to
         determine the region (e.g. ".HK" → "Hong Kong", no suffix → "USA").
      3. Aggregate weights by region; residual → "Other".
      4. Normalise to sum = 100.

    Cached 24 h.
    """
    key = f"geo_{ticker_yf}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    _load_metadata_csv()
    if key in _CSV_CACHE_STORE:
        result = _CSV_CACHE_STORE[key]
        _cache_set(key, result, _GEO_TTL)
        return result

    try:
        tk = get_ticker_cached(ticker_yf)
        fd = tk.funds_data
        df = fd.top_holdings   # index=Symbol, col="Holding Percent" (0–1)

        if df is None or df.empty:
            result = {"Unclassified": 100.0}
            _cache_set(key, result, 300)
            return result

        region_weights: dict[str, float] = {}
        accounted = 0.0

        for symbol, row in df.iterrows():
            pct = float(row.get("Holding Percent", 0)) * 100
            if pct <= 0:
                continue
            region = _symbol_to_region(str(symbol))
            region_weights[region] = region_weights.get(region, 0) + pct
            accounted += pct

        # Remaining weight → Other (holdings below the top-N cutoff)
        residual = max(0.0, 100.0 - accounted)
        if residual > 0.5:
            region_weights["Other"] = region_weights.get("Other", 0) + residual

        total = sum(region_weights.values())
        result = {k: round(v / total * 100, 1) for k, v in region_weights.items()} \
                 if total > 0 else {"Unclassified": 100.0}
        result = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

        _cache_set(key, result, _GEO_TTL)
        _CSV_CACHE_STORE[key] = result
        _append_metadata_csv(ticker_yf, "geo", result)
        logger.debug("Geo %s: %s", ticker_yf, result)
        return result

    except Exception as exc:
        logger.warning("Geo fetch failed %s: %s", ticker_yf, exc)
        result = {"Unclassified": 100.0}
        _cache_set(key, result, 300)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
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


# ─────────────────────────────────────────────────────────────────────────────
# Risk metrics
# ─────────────────────────────────────────────────────────────────────────────

def portfolio_returns(histories: dict, holdings: list[dict]) -> pd.Series:
    ret_df  = _histories_to_returns(histories)
    weights = _portfolio_weights(holdings)
    if ret_df.empty or not weights:
        return pd.Series(dtype=float)
    common = [t for t in weights if t in ret_df.columns]
    if not common:
        return pd.Series(dtype=float)
    w = pd.Series({t: weights[t] for t in common})
    w = w / w.sum()
    return ret_df[common].mul(w, axis=1).sum(axis=1).dropna()


def annualised_volatility(returns: pd.Series) -> float:
    if returns.empty or len(returns) < 5:
        return float("nan")
    return round(float(returns.std() * math.sqrt(252) * 100), 2)


def sharpe_ratio(returns: pd.Series) -> float:
    if returns.empty or len(returns) < 5:
        return float("nan")
    excess = returns - RISK_FREE_DAILY
    if excess.std() == 0:
        return float("nan")
    return round(float(excess.mean() / excess.std() * math.sqrt(252)), 2)


def max_drawdown(returns: pd.Series) -> float:
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
             if len(ret_df[col].dropna()) >= 5 else float("nan")
        for col in ret_df.columns
    }


def compute_risk_metrics(port_data: dict, period: str = "max") -> dict:
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

    # ── Cards: use full history ──────────────────────────────────────────────
    vol     = annualised_volatility(port_ret)
    sharpe  = sharpe_ratio(port_ret)
    max_dd  = max_drawdown(port_ret)
    cur_dd  = round(float(drawdown_series(port_ret).iloc[-1]), 2) if not port_ret.empty else None

    # ── Charts: apply period filter ──────────────────────────────────────────
    chart_ret = port_ret
    cutoff = get_period_cutoff(period)
    if cutoff is not None:
        chart_ret = port_ret[port_ret.index >= cutoff]

    if chart_ret.empty:
        # If filtered period is empty, return empty charts but keep cards
        return {
            "vol": vol, "sharpe": sharpe, "max_dd": max_dd, "current_dd": cur_dd,
            "ticker_vols": per_ticker_volatility(histories),
            "dd_dates": [], "dd_values": [],
            "ret_dates": [], "ret_values": [], "n_days": len(port_ret),
        }

    dd_s    = drawdown_series(chart_ret)
    cum_ret = ((1 + chart_ret).cumprod() - 1) * 100

    return {
        "vol":         vol,
        "sharpe":      sharpe,
        "max_dd":      max_dd,
        "current_dd":  cur_dd,
        "ticker_vols": per_ticker_volatility(histories),
        "dd_dates":    fmt_date_index(dd_s.index),
        "dd_values":   dd_s.tolist(),
        "ret_dates":   fmt_date_index(cum_ret.index),
        "ret_values":  cum_ret.round(2).tolist(),
        "n_days":      len(port_ret),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Allocation insights
# ─────────────────────────────────────────────────────────────────────────────

def _get_full_exposure(port_data: dict, fetch_fn) -> dict[str, float]:
    holdings = port_data.get("holdings", [])
    weights  = _portfolio_weights(holdings)
    blended: dict[str, float] = {}

    for h in holdings:
        ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
        port_w    = weights.get(h["ticker"], 0)
        if port_w <= 0:
            continue
        for category, pct in fetch_fn(ticker_yf).items():
            blended[category] = blended.get(category, 0) + port_w * pct

    total = sum(blended.values())
    if total > 0:
        return {k: round(v / total * 100, 1) for k, v in blended.items()}
    return {}

def _group_exposure(full_exp: dict[str, float]) -> dict[str, float]:
    sorted_blended = sorted(full_exp.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_blended) > 7:
        top_6 = sorted_blended[:6]
        other_sum = sum(v for k, v in sorted_blended[6:])
        
        # If 'Other' already existed in top_6, combine them, otherwise just append
        existing_other = next((i for i, (k, _) in enumerate(top_6) if k == "Other"), None)
        if existing_other is not None:
            top_6[existing_other] = ("Other", round(top_6[existing_other][1] + other_sum, 1))
        else:
            top_6.append(("Other", round(other_sum, 1)))
        return dict(top_6)
    return dict(sorted_blended)

def sector_exposure(port_data: dict) -> dict[str, float]:
    """Portfolio-weighted sector blend from live yfinance funds_data."""
    full = _get_full_exposure(port_data, fetch_etf_sector_weights)
    return _group_exposure(full)

def geo_exposure(port_data: dict) -> dict[str, float]:
    """Portfolio-weighted geographic blend inferred from top-holdings symbols."""
    full = _get_full_exposure(port_data, fetch_etf_geo_weights)
    return _group_exposure(full)

def get_exposure_detail(port_data: dict, exposure_type: str, category_name: str) -> list[dict]:
    """
    Returns breakdown of which tickers contribute to a specific sector/region.
    Handles 'Other' by finding all minor categories grouped into it.
    """
    holdings = port_data.get("holdings", [])
    weights  = _portfolio_weights(holdings)
    
    if exposure_type == "sector":
        full_exp = _get_full_exposure(port_data, fetch_etf_sector_weights)
        fetch_fn = fetch_etf_sector_weights
    else:
        full_exp = _get_full_exposure(port_data, fetch_etf_geo_weights)
        fetch_fn = fetch_etf_geo_weights
        
    sorted_exp = sorted(full_exp.items(), key=lambda x: x[1], reverse=True)
    top_categories = {k for k, v in sorted_exp[:6]} if len(sorted_exp) > 7 else {k for k, v in sorted_exp}
    
    is_other_request = (category_name == "Other")
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
                
            match = False
            if is_other_request:
                # 'Other' catches anything not in top 6, plus anything explicitly named 'Other'
                if cat not in top_categories or cat == "Other":
                    match = True
            elif cat == category_name:
                match = True
                
            if match:
                detail.append({
                    "ticker": ticker,
                    "weight": contribution, # Removed rounding to prevent Sunburst hierarchy sum errors
                    "sub_category": cat
                })
    
    return sorted(detail, key=lambda x: x["weight"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Smart alerts
# ─────────────────────────────────────────────────────────────────────────────

def compute_smart_alerts(metrics: dict, port_data: dict) -> list[dict]:
    alerts: list[dict] = []
    holdings = port_data.get("holdings", [])
    if not holdings:
        return alerts

    weights      = _portfolio_weights(holdings)
    sec_exp      = sector_exposure(port_data)
    geo_exp_data = geo_exposure(port_data)

    # Single ETF concentration
    for ticker, w in weights.items():
        pct = round(w * 100, 1)
        if pct >= THRESHOLDS["single_etf_weight"]:
            alerts.append({
                "level": "warning", "icon": "⚖",
                "title": f"{ticker} is {pct}% of your portfolio",
                "detail": f"A single ETF above {THRESHOLDS['single_etf_weight']:.0f}% "
                          "concentrates risk. Consider rebalancing.",
            })

    # Sector overweight
    for sector, pct in sec_exp.items():
        if sector in ("Other", "Unclassified"):
            continue
        if pct >= THRESHOLDS["sector_overweight"]:
            alerts.append({
                "level": "warning", "icon": "🏭",
                "title": f"Overweight {sector} ({pct}%)",
                "detail": f"More than {THRESHOLDS['sector_overweight']:.0f}% in one "
                          "sector increases idiosyncratic risk.",
            })

    # Tech tighter threshold
    tech_pct = sec_exp.get("Technology", 0)
    if THRESHOLDS["tech_overweight"] <= tech_pct < THRESHOLDS["sector_overweight"]:
        alerts.append({
            "level": "warning", "icon": "💻",
            "title": f"High Technology exposure ({tech_pct}%)",
            "detail": "Technology is historically more volatile than the broad market.",
        })

    # Geographic concentration
    for region, pct in geo_exp_data.items():
        if region in ("Other", "Unclassified"):
            continue
        if pct >= THRESHOLDS["geo_overweight"]:
            alerts.append({
                "level": "info", "icon": "🌏",
                "title": f"Heavy {region} exposure ({pct}%)",
                "detail": f"Over {THRESHOLDS['geo_overweight']:.0f}% in one region "
                          "reduces geographic diversification.",
            })

    # Volatility
    vol = metrics.get("vol")
    if vol is not None and not math.isnan(vol) and vol >= THRESHOLDS["high_vol_annualised"]:
        alerts.append({
            "level": "warning", "icon": "📈",
            "title": f"Portfolio volatility elevated ({vol:.1f}% p.a.)",
            "detail": f"Annualised vol above {THRESHOLDS['high_vol_annualised']:.0f}% "
                      "means higher short-term price swings.",
        })

    # Sharpe
    sharpe = metrics.get("sharpe")
    if sharpe is not None and not math.isnan(sharpe):
        if sharpe < THRESHOLDS["low_sharpe"]:
            alerts.append({
                "level": "info", "icon": "📉",
                "title": f"Low risk-adjusted return (Sharpe {sharpe:.2f})",
                "detail": "A Sharpe below 0.5 means risk taken isn't justified "
                          "vs the RBA cash rate.",
            })
        elif sharpe >= 1.5:
            alerts.append({
                "level": "info", "icon": "⭐",
                "title": f"Strong risk-adjusted return (Sharpe {sharpe:.2f})",
                "detail": "A Sharpe above 1.5 is excellent — strong returns per unit of risk.",
            })

    # Drawdown
    current_dd = metrics.get("current_dd")
    if current_dd is not None and not math.isnan(current_dd) \
            and current_dd <= THRESHOLDS["bad_drawdown"]:
        alerts.append({
            "level": "danger", "icon": "🔻",
            "title": f"Portfolio in drawdown ({current_dd:.1f}%)",
            "detail": f"Portfolio is {abs(current_dd):.1f}% below its recent peak.",
        })

    # Note unclassified tickers
    unclassified = sec_exp.get("Unclassified", 0)
    if unclassified > 5:
        unknown = [h["ticker"] for h in holdings
                   if _cache_get(f"sector_{h.get('ticker_yf', h['ticker']+'.AX')}")
                   == {"Unclassified": 100.0}]
        if unknown:
            alerts.append({
                "level": "info", "icon": "❓",
                "title": f"{unclassified:.0f}% of portfolio unclassified",
                "detail": f"No sector/geo data from Yahoo for: {', '.join(unknown)}.",
            })

    if not alerts:
        alerts.append({
            "level": "info", "icon": "✅",
            "title": "Portfolio looks well-balanced",
            "detail": "No concentration, volatility, or drawdown alerts at this time.",
        })

    return alerts