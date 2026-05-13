"""
services/market/holdings_fetcher.py
===================================
Fetches and caches ETF holdings data using a 3-tier architecture.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import json

from data.database import get_connection
from services.intelligence_service import _get_cached_metadata, _save_metadata

logger = logging.getLogger(__name__)

PROVIDER_URLS = {
    "VHY": "https://www.vanguard.com.au/personal/products/en/detail/8210/portfolio",
    "IOZ": "https://www.blackrock.com/au/individual/products/227573/ishares-core-sp-asx-200-etf/1518043690623.ajax?fileType=csv&fileName=IOZ_holdings&dataType=fund",
    "IOO": "https://www.blackrock.com/au/individual/products/227546/ishares-global-100-etf/1518043690623.ajax?fileType=csv&fileName=IOO_holdings&dataType=fund",
    "AINF": "https://www.blackrock.com/au/individual/products/328292/ishares-asx-200-etf/1518043690623.ajax?fileType=csv&fileName=AINF_holdings&dataType=fund",
    "ASIA": "https://www.betashares.com.au/fund/asia-technology-tigers-etf/",
    "SEMI": "https://www.betashares.com.au/fund/global-semiconductor-etf/",
    "XMET": "https://www.betashares.com.au/fund/energy-transition-metals-etf/",
    "QUAL": "https://www.vaneck.com.au/etf/equity/qual/holdings/"
}

HOLDINGS_TTL_DAYS = 30
RETRY_HOURS = 24

def _check_throttle(ticker: str) -> bool:
    """Returns True if we should SKIP fetching due to recent failure."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT last_attempt FROM etf_holdings_attempts WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if not row:
            return False
        
        last_attempt = pd.to_datetime(row["last_attempt"])
        age_hours = (pd.Timestamp.now() - last_attempt).total_seconds() / 3600
        return age_hours < RETRY_HOURS
    finally:
        conn.close()

def _record_attempt(ticker: str, error: str = None):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO etf_holdings_attempts (ticker, last_attempt, last_error) 
            VALUES (?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(ticker) DO UPDATE SET 
            last_attempt = CURRENT_TIMESTAMP,
            last_error = excluded.last_error
            """,
            (ticker, error)
        )
        conn.commit()
    finally:
        conn.close()

def _clear_throttle(ticker: str):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM etf_holdings_attempts WHERE ticker = ?", (ticker,))
        conn.commit()
    finally:
        conn.close()

def _normalize_holdings(raw_dict: dict) -> dict:
    """Ensures holdings sum correctly, truncates small items into 'Other' if needed."""
    if not raw_dict or len(raw_dict) < 5:
        return {}
        
    result = {}
    other = 0.0
    for k, v in raw_dict.items():
        try:
            val = float(v)
            if val <= 0: continue
            result[str(k).strip()] = val
        except (ValueError, TypeError):
            continue
            
    if not result:
        return {}
        
    # Standardize weights
    total = sum(result.values())
    if total < 1.0: # assume fractional 0.0-1.0
        result = {k: v * 100 for k, v in result.items()}
        total = sum(result.values())
        
    # Scale to 100 if very close
    if 98.0 <= total <= 102.0:
        factor = 100.0 / total
        result = {k: v * factor for k, v in result.items()}
    elif total < 98.0:
        result["Other"] = 100.0 - total
        
    # Return top holdings (keep reasonable number)
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True)[:50])

def _fetch_tier1(ticker: str, url: str) -> dict:
    """Tier 1: Direct CSV/JSON API calls."""
    if "fileType=csv" not in url:
        return {} # Only handle CSVs here currently
        
    logger.debug(f"[{ticker}] Tier 1 Fetching CSV: {url}")
    try:
        import io
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text), skiprows=2) # Blackrock typical format
        
        # Try to find relevant columns
        cols = [c.lower() for c in df.columns]
        
        name_col = None
        for cand in ["name", "issuer", "company"]:
            if cand in cols: name_col = df.columns[cols.index(cand)]; break
            
        weight_col = None
        for cand in ["weight", "weight (%)", "fund weight (%)", "% of net assets"]:
            if cand in cols: weight_col = df.columns[cols.index(cand)]; break
            
        if not name_col or not weight_col:
            return {}
            
        holdings = {}
        for _, row in df.iterrows():
            name = str(row[name_col])
            weight = str(row[weight_col]).replace("%", "").replace(",", "")
            if name and name != "nan" and weight and weight != "nan":
                holdings[name] = float(weight)
                
        return holdings
    except Exception as e:
        logger.debug(f"[{ticker}] Tier 1 failed: {e}")
        return {}

def _discover_url(ticker: str, provider: str = "ETF") -> str:
    """Tier 1.5: DuckDuckGo Search for the holdings page."""
    try:
        logger.debug(f"[{ticker}] Tier 1.5 DDGS URL discovery...")
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{ticker} {provider} ETF portfolio holdings site:com.au", max_results=3))
            for res in results:
                url = res.get("href", "")
                if "holdings" in url.lower() or "portfolio" in url.lower():
                    return url
    except Exception as e:
        logger.debug(f"[{ticker}] DDGS discovery failed: {e}")
        
    return PROVIDER_URLS.get(ticker, "")

def _scrape_with_playwright(url: str, ticker: str) -> dict:
    """Tier 2: Headless WebKit Playwright fallback."""
    if not url: return {}
    logger.debug(f"[{ticker}] Tier 2 Playwright scraping: {url}")
    
    from playwright.sync_api import sync_playwright
    
    holdings = {}
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_selector('table', timeout=15000)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 5: continue
                
                # Check headers
                headers = [th.text.strip().lower() for th in rows[0].find_all(["th", "td"])]
                
                name_idx = -1
                weight_idx = -1
                
                for i, h in enumerate(headers):
                    if any(x in h for x in ["name", "security", "holding", "issuer", "company"]):
                        name_idx = i
                    if any(x in h for x in ["weight", "%", "portfolio"]):
                        weight_idx = i
                        
                if name_idx == -1 or weight_idx == -1:
                    continue
                    
                table_holdings = {}
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) > max(name_idx, weight_idx):
                        name = cols[name_idx].text.strip()
                        weight_str = cols[weight_idx].text.strip().replace("%", "").replace(",", "")
                        try:
                            weight = float(weight_str)
                            if name and weight > 0:
                                table_holdings[name] = weight
                        except ValueError:
                            pass
                            
                if len(table_holdings) > len(holdings):
                    holdings = table_holdings
                    
        except Exception as e:
            logger.debug(f"[{ticker}] Tier 2 Playwright failed: {e}")
        finally:
            browser.close()
            
    return holdings

def fetch_holdings(ticker: str) -> dict:
    """
    Main entry point for fetching ETF holdings.
    Returns: { "Company Name": weight_percentage, ... }
    """
    ticker_yf = ticker + ".AX"
    
    # 1. Check SQLite Cache
    cached = _get_cached_metadata(ticker_yf, "holdings", ttl_days=HOLDINGS_TTL_DAYS)
    if cached:
        return cached
        
    if _check_throttle(ticker):
        logger.debug(f"[{ticker}] Skipping fetch due to recent failure (throttled)")
        return {}
        
    url = PROVIDER_URLS.get(ticker, "")
    
    # Tier 1
    holdings = _fetch_tier1(ticker, url)
    
    # Tier 1.5 + Tier 2
    if not holdings:
        discovered_url = _discover_url(ticker)
        target_url = discovered_url or url
        holdings = _scrape_with_playwright(target_url, ticker)
        
    holdings = _normalize_holdings(holdings)
    
    if holdings:
        _save_metadata(ticker_yf, "holdings", holdings)
        _clear_throttle(ticker)
        logger.info(f"[{ticker}] Successfully fetched {len(holdings)} holdings.")
        return holdings
    else:
        _record_attempt(ticker, "Failed all tiers")
        return {}
