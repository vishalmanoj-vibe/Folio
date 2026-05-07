# services/market/dividend_service.py
import logging
import pandas as pd
from config.settings import DIVIDENDS_CACHE_TTL
from core import get_cache, set_cache
from services.market.data_fetcher import _download_with_retry, _extract_col
from core.engine.utils import normalise_tz

logger = logging.getLogger(__name__)

# Known/Confirmed Dividend Dates (Fallback for missing yfinance metadata)
CONFIRMED_PAY_DATES = {
    ("VHY", "2026-04-01"): "2026-04-20",
    ("IOZ", "2026-04-09"): "2026-04-21",
}

def get_ticker_dividend_data(ticker, ticker_yf):
    """
    Fetches historical dividends for a specific ticker.
    Uses per-ticker caching.
    """
    cache_key = f"dividend_{ticker}"
    cached = get_cache(cache_key)
    if cached is not None:
        # If cached is a dict (legacy) or other format, handle it
        if isinstance(cached, pd.DataFrame):
            return cached

    try:
        logger.debug(f"Fetching dividend history for {ticker}")
        bulk_df = _download_with_retry([ticker_yf], period="max", actions=True)
        if bulk_df.empty:
            return pd.DataFrame()

        div_s = _extract_col(bulk_df, ticker_yf, "Dividends")
        if div_s.empty:
            df = pd.DataFrame()
            set_cache(cache_key, df, ttl=DIVIDENDS_CACHE_TTL)
            return df

        div_s = div_s[div_s > 0]
        div_s.index = normalise_tz(div_s.index)

        div_list = []
        for ex_date, amount in div_s.items():
            ex_date_str = ex_date.strftime("%Y-%m-%d")
            pay_date = CONFIRMED_PAY_DATES.get((ticker, ex_date_str))
            
            div_list.append({
                "date": ex_date,
                "pay_date": pay_date,
                "ticker": ticker,
                "amount": float(amount)
            })

        df = pd.DataFrame(div_list).sort_values("date", ascending=False)
        set_cache(cache_key, df, ttl=DIVIDENDS_CACHE_TTL)
        return df
    except Exception as e:
        logger.error(f"Failed to fetch dividends for {ticker}: {e}")
        return pd.DataFrame()

def calculate_portfolio_dividend_stats(holdings):
    """
    Aggregates dividend data from all holdings.
    Returns: (all_distributions_df, kpi_stats, events)
    """
    all_divs = []
    for h in holdings:
        ticker = h["ticker"]
        ticker_yf = h["ticker_yf"]
        tranches = h.get("buy_tranches", [])
        
        df = get_ticker_dividend_data(ticker, ticker_yf)
        if df.empty: continue
        
        # Calculate eligibility and totals based on tranches
        for _, row in df.iterrows():
            ex_date = row["date"]
            # A tranche is eligible only if it was bought BEFORE the ex-dividend date
            held_on_date = sum(t["shares"] for t in tranches if pd.to_datetime(t["date"]) < ex_date)
            if held_on_date > 0:
                pay_date = row["pay_date"]
                # Fallback pay_date if it matches last dividend metadata
                if not pay_date and h.get("last_div_date") == ex_date.strftime("%Y-%m-%d"):
                    pay_date = h.get("payout_date")
                    
                all_divs.append({
                    "date": ex_date,
                    "pay_date": pay_date,
                    "ticker": ticker,
                    "amount": row["amount"],
                    "total": row["amount"] * held_on_date,
                    "shares": held_on_date
                })

    df_full = pd.DataFrame(all_divs).sort_values("date", ascending=False) if all_divs else pd.DataFrame()
    
    # KPI Stats
    total_realized = df_full["total"].sum() if not df_full.empty else 0
    annual_est = sum(h.get("annual_div", 0) for h in holdings)
    port_total_val = sum(h["mkt_value"] for h in holdings)
    port_yield = (annual_est / port_total_val * 100) if port_total_val else 0
    
    stats = {
        "annual_income": annual_est,
        "portfolio_yield": port_yield,
        "total_realized": total_realized
    }
    
    # Events (Calendar)
    today = pd.Timestamp.now().floor("D")
    events = []
    f_map = {"Monthly": 1, "Quarterly": 3, "Biannual": 6, "Annual": 12, "Unknown": 3}
    
    for h in holdings:
        payout_dt = h.get("payout_date")
        next_ex_dt = h.get("next_div_date")
        
        if payout_dt:
            events.append({
                "ticker": h["ticker"], "date": pd.to_datetime(payout_dt),
                "amount": h.get("last_div_amount", 0),
                "total": h.get("last_div_amount", 0) * h["total_shares"],
                "type": "PAYMENT"
            })
        elif next_ex_dt:
            events.append({
                "ticker": h["ticker"], "date": pd.to_datetime(next_ex_dt),
                "amount": h.get("last_div_amount", 0),
                "total": h.get("last_div_amount", 0) * h["total_shares"],
                "type": "EX-DATE"
            })
        else:
            last_dt = h.get("last_div_date")
            if last_dt:
                next_ex = pd.to_datetime(last_dt) + pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                while next_ex < today:
                    next_ex += pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                
                events.append({
                    "ticker": h["ticker"], "date": next_ex,
                    "amount": h.get("last_div_amount", 0),
                    "total": h.get("last_div_amount", 0) * h["total_shares"],
                    "type": "ESTIMATED"
                })
    
    events = sorted(events, key=lambda x: x["date"])
    
    # Find next payment info
    next_payment = next((e for e in events if e["date"] >= today), None)
    stats["next_payment"] = next_payment
    
    return df_full, stats, events
