"""
services/market/holdings_fetcher.py
=====================================
Fetches and caches ETF holdings data using a dynamic 5-strategy architecture.

Provider detection is based on the seed URL — each provider has a known scraping
strategy. No AJAX IDs or internal endpoints need to be hardcoded.

Tier 1 – BetaShares   : Static HTML, table with 10+ cols
Tier 1 – Global X     : Static HTML, table 0 (Net Assets %, Name)
Tier 1 – BlackRock    : 2-step: extract AJAX CSV ID from page → download CSV
Tier 1 – VanEck       : 2-step: extract JSON-LD API URL → call JSON API
Tier 2 – Vanguard     : Playwright SPA (JS-rendered page)
Tier 3 – Unknown      : DDGS URL discovery + Playwright fallback
"""

import io
import json
import logging
import re
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data.database import get_connection
from services.intelligence_service import _get_cached_metadata, _save_metadata

logger = logging.getLogger(__name__)

# ── Seed URL Registry ─────────────────────────────────────────────────────────
# One product-page URL per known ticker. Add new tickers here as a single line.
# Unknown tickers fall through to DDGS + Playwright automatically.
PROVIDER_SEED_URLS: dict[str, str] = {
    # BetaShares
    "URNM": "https://www.betashares.com.au/fund/global-uranium-etf/",
    "XMET": "https://www.betashares.com.au/fund/energy-transition-metals-etf/",
    "ASIA": "https://www.betashares.com.au/fund/asia-technology-tigers-etf/",
    # Global X
    "AINF": "https://www.globalxetfs.com.au/funds/ainf/",
    "SEMI": "https://www.globalxetfs.com.au/funds/semi/",
    # BlackRock (iShares)
    "IOZ": "https://www.blackrock.com/au/products/251852/ishares-core-s-and-p-asx-200-etf",
    "IOO": "https://www.blackrock.com/au/products/273428/ishares-global-100-etf",
    # Vanguard Australia (SPA – requires Playwright)
    "VHY": "https://www.vanguard.com.au/adviser/invest/etf?portId=8210&tab=portfolio-data",
    # VanEck
    "QUAL": "https://www.vaneck.com.au/etf/equity/qual/snapshot/",
}

# ── Constants ──────────────────────────────────────────────────────────────────
HOLDINGS_TTL_DAYS = 30
RETRY_HOURS = 24
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Throttle helpers ──────────────────────────────────────────────────────────


def _check_throttle(ticker: str) -> bool:
    """Returns True if we should SKIP fetching due to recent failure."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT last_attempt FROM etf_holdings_attempts WHERE ticker = ?", (ticker,)
        )
        row = cur.fetchone()
        if not row:
            return False
        last_attempt = pd.to_datetime(row["last_attempt"])
        age_hours = (pd.Timestamp.now() - last_attempt).total_seconds() / 3600
        return age_hours < RETRY_HOURS
    finally:
        conn.close()


def _record_attempt(ticker: str, error: str | None = None):
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
            (ticker, error),
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


# ── Normalisation ─────────────────────────────────────────────────────────────


def _normalize_holdings(raw_dict: dict) -> dict:
    """Ensures holdings sum correctly, truncates small items into 'Other'."""
    if not raw_dict or len(raw_dict) < 5:
        return {}

    result = {}
    for k, v in raw_dict.items():
        try:
            val = float(v)
            if val <= 0:
                continue
            result[str(k).strip()] = val
        except (ValueError, TypeError):
            continue

    if not result:
        return {}

    total = sum(result.values())
    if total < 1.0:  # fractional weights (0.0–1.0) → scale to percentage
        result = {k: v * 100 for k, v in result.items()}
        total = sum(result.values())

    if 98.0 <= total <= 102.0:
        factor = 100.0 / total
        result = {k: v * factor for k, v in result.items()}
    elif total < 98.0:
        result["Other"] = 100.0 - total

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True)[:50])


# ── Sector/Geo helpers ────────────────────────────────────────────────────────


def _save_sector_geo_from_holdings(
    ticker_yf: str,
    sector_map: dict[str, float],
    geo_map: dict[str, float],
) -> None:
    """Persist sector and geo breakdowns derived from scraped holdings data."""
    if sector_map:
        _save_metadata(ticker_yf, "sector", sector_map)
        logger.debug(f"[{ticker_yf}] Saved {len(sector_map)} sector weights from scrape.")
    if geo_map:
        _save_metadata(ticker_yf, "geo", geo_map)
        logger.debug(f"[{ticker_yf}] Saved {len(geo_map)} geo weights from scrape.")


def _aggregate_weights(col_data: list[tuple[str, float]]) -> dict[str, float]:
    """Sum weights by category and normalise to 100%."""
    agg: dict[str, float] = {}
    for category, weight in col_data:
        if not category or category.lower() in ("nan", "", "n/a", "-"):
            continue
        agg[category] = round(agg.get(category, 0.0) + weight, 4)

    total = sum(agg.values())
    if total <= 0:
        return {}
    return {k: round(v / total * 100, 2) for k, v in agg.items()}


# ── Provider: BetaShares ──────────────────────────────────────────────────────


def _fetch_betashares(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """
    Scrapes the BetaShares fund page.
    Holdings table (Table 7 typically) has columns:
      0: ASX code, 1: Company Name, 2: Weight (%), 3: Asset Class,
      4: Sector, 5: Country/Location, ...

    Returns: (holdings, sector_map, geo_map)
    """
    logger.debug(f"[{ticker}] BetaShares static HTML scrape: {url}")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table")

        # Find the large holdings table (10+ columns)
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            header_cells = rows[0].find_all(["th", "td"])
            if len(header_cells) < 8:
                continue

            holdings: dict[str, float] = {}
            sectors: list[tuple[str, float]] = []
            geos: list[tuple[str, float]] = []

            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                name = cols[1].text.strip()
                weight_str = cols[2].text.strip().replace("%", "").replace(",", "")
                try:
                    weight = float(weight_str)
                except ValueError:
                    continue
                if not name or weight <= 0:
                    continue

                holdings[name] = weight

                sector = cols[4].text.strip() if len(cols) > 4 else ""
                country = cols[5].text.strip() if len(cols) > 5 else ""
                if sector:
                    sectors.append((sector, weight))
                if country:
                    geos.append((country, weight))

            if len(holdings) >= 5:
                return holdings, _aggregate_weights(sectors), _aggregate_weights(geos)

    except Exception as e:
        logger.debug(f"[{ticker}] BetaShares scrape failed: {e}")

    return {}, {}, {}


# ── Provider: Global X ────────────────────────────────────────────────────────


def _fetch_globalx(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """
    Scrapes the Global X ETF fund page.
    Table 0 has columns: Net Assets (%), Name, SEDOL, Market Price, Shares Held, Market Value

    Returns: (holdings, sector_map, geo_map) — no sector/geo available from Global X
    """
    logger.debug(f"[{ticker}] Global X static HTML scrape: {url}")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            header_cells = [h.text.strip() for h in rows[0].find_all(["th", "td"])]
            # Identify Global X table by its specific header pattern
            if len(header_cells) < 2:
                continue
            if "Net Assets" not in header_cells[0] and "Net Assets" not in " ".join(
                header_cells[:3]
            ):
                continue

            holdings: dict[str, float] = {}
            for row in rows[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) < 2:
                    continue
                weight_str = cols[0].text.strip().replace("%", "").replace(",", "")
                name = cols[1].text.strip()
                try:
                    weight = float(weight_str)
                except ValueError:
                    continue
                if not name or weight <= 0:
                    continue
                holdings[name] = weight

            if len(holdings) >= 5:
                return holdings, {}, {}

    except Exception as e:
        logger.debug(f"[{ticker}] Global X scrape failed: {e}")

    return {}, {}, {}


# ── Provider: BlackRock (iShares) ─────────────────────────────────────────────


def _fetch_blackrock(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """
    2-step BlackRock scrape:
    1. Fetch product page, extract AJAX CSV download URL from 'Download Holdings' link
    2. Download CSV → parse Name, Weight (%), Sector, Location columns

    Returns: (holdings, sector_map, geo_map)
    """
    logger.debug(f"[{ticker}] BlackRock 2-step scrape: {url}")
    try:
        # Step 1: Get product page and find CSV AJAX link
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()

        # Extract the holdings CSV AJAX path from the "Download Holdings" anchor
        csv_match = re.search(
            r'href="(/au/products/\d+/fund/(\d+)\.ajax\?fileType=csv[^"]*)"', r.text
        )
        if not csv_match:
            logger.debug(f"[{ticker}] BlackRock: No CSV link found in product page.")
            return {}, {}, {}

        ajax_path = csv_match.group(1)
        csv_url = "https://www.blackrock.com" + ajax_path
        logger.debug(f"[{ticker}] BlackRock CSV URL discovered: {csv_url}")

        # Step 2: Download CSV
        csv_headers = dict(_HEADERS)
        csv_headers["Referer"] = url
        csv_headers["Accept"] = "text/csv,application/json,*/*"
        r2 = requests.get(csv_url, headers=csv_headers, timeout=15)
        r2.raise_for_status()

        content_type = r2.headers.get("content-type", "")
        if "csv" not in content_type and "text" not in content_type:
            logger.debug(f"[{ticker}] BlackRock: Unexpected content type: {content_type}")
            return {}, {}, {}

        # Parse CSV — BlackRock format has a 1-line date header, then column headers
        lines = r2.text.splitlines()
        # Find the header row (contains "Name" or "Ticker")
        header_idx = 0
        for i, line in enumerate(lines):
            if "Name" in line or "Ticker" in line:
                header_idx = i
                break

        csv_text = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(csv_text))

        # Normalise column names
        df.columns = [c.strip() for c in df.columns]
        col_map = {c.lower(): c for c in df.columns}

        name_col = next((col_map[k] for k in ["name"] if k in col_map), None)
        weight_col = next(
            (col_map[k] for k in ["weight (%)", "weight(%)", "weight"] if k in col_map), None
        )
        sector_col = col_map.get("sector")
        loc_col = next((col_map[k] for k in ["location"] if k in col_map), None)

        if not name_col or not weight_col:
            logger.debug(
                f"[{ticker}] BlackRock: Could not identify Name/Weight columns. Cols: {list(df.columns)}"
            )
            return {}, {}, {}

        holdings: dict[str, float] = {}
        sectors: list[tuple[str, float]] = []
        geos: list[tuple[str, float]] = []

        # Identify Asset Class column to filter out Cash/Derivatives/self-references
        asset_col = col_map.get("asset class")

        for _, row in df.iterrows():
            name = str(row.get(name_col, "")).strip()
            weight_raw = str(row.get(weight_col, "")).replace("%", "").replace(",", "").strip()
            try:
                weight = float(weight_raw)
            except ValueError:
                continue
            if not name or name.lower() in ("nan", "") or weight <= 0:
                continue

            # Skip self-referencing ETF wrapper rows (weight near 100%) and non-equity
            if weight > 95.0:
                continue
            if asset_col:
                asset_class = str(row.get(asset_col, "")).strip().lower()
                if asset_class and "equity" not in asset_class:
                    continue

            holdings[name] = weight

            if sector_col:
                sector = str(row.get(sector_col, "")).strip()
                if sector and sector.lower() not in ("nan", "", "cash and/or derivatives"):
                    sectors.append((sector, weight))
            if loc_col:
                loc = str(row.get(loc_col, "")).strip()
                if loc and loc.lower() not in ("nan", ""):
                    geos.append((loc, weight))

        if len(holdings) >= 5:
            return holdings, _aggregate_weights(sectors), _aggregate_weights(geos)

    except Exception as e:
        logger.debug(f"[{ticker}] BlackRock scrape failed: {e}")

    return {}, {}, {}


# ── Provider: VanEck ─────────────────────────────────────────────────────────


def _fetch_vaneck(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """
    2-step VanEck scrape:
    1. Fetch snapshot page, extract JSON-LD 'contentUrl' API endpoint
    2. Call JSON API → parse HoldingsList[].Holdings[]: Weight, HoldingName, Sector, Country

    Returns: (holdings, sector_map, geo_map)
    """
    logger.debug(f"[{ticker}] VanEck 2-step JSON API scrape: {url}")
    try:
        # Step 1: Get snapshot page and find the JSON API URL from Schema.org JSON-LD
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()

        api_match = re.search(
            r'"contentUrl":\s*"(https://www\.vaneck\.com\.au/Main/FundDatasetBlock/Get/[^"]+)"',
            r.text,
        )
        if not api_match:
            logger.debug(f"[{ticker}] VanEck: No JSON-LD contentUrl found.")
            return {}, {}, {}

        api_url = api_match.group(1)
        logger.debug(f"[{ticker}] VanEck API URL discovered: {api_url}")

        # Step 2: Call JSON API
        api_headers = dict(_HEADERS)
        api_headers["Accept"] = "application/json, */*"
        api_headers["Referer"] = url
        r2 = requests.get(api_url, headers=api_headers, timeout=15)
        r2.raise_for_status()

        data = r2.json()
        holdings_list = data.get("HoldingsList", [])
        if not holdings_list:
            return {}, {}, {}

        # Use the first (most recent) date's holdings
        holding_entries = holdings_list[0].get("Holdings", [])

        holdings: dict[str, float] = {}
        sectors: list[tuple[str, float]] = []
        geos: list[tuple[str, float]] = []

        for entry in holding_entries:
            label_type = entry.get("LabelType", "")
            if label_type != "Holdings":
                continue

            name = entry.get("HoldingName", "").strip()
            weight_raw = str(entry.get("Weight", "0")).replace("%", "").strip()
            try:
                weight = float(weight_raw)
            except ValueError:
                continue
            if not name or weight <= 0:
                continue

            holdings[name] = weight

            sector = entry.get("Sector", "").strip()
            country = entry.get("Country", "").strip()
            if sector:
                sectors.append((sector, weight))
            if country:
                geos.append((country, weight))

        if len(holdings) >= 5:
            return holdings, _aggregate_weights(sectors), _aggregate_weights(geos)

    except Exception as e:
        logger.debug(f"[{ticker}] VanEck scrape failed: {e}")

    return {}, {}, {}


# ── Provider: Vanguard (Playwright SPA) ───────────────────────────────────────


def _fetch_vanguard_playwright(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """
    Vanguard AU uses an Angular SPA. Instead of parsing the top-10 rendered table,
    we intercept the 'Download all' Excel button click to get all holdings.

    Excel structure (row 2 = headers, data from row 3):
      Holding Name | Ticker | Sector | Country code | % of net assets | Market value | # of units

    Returns: (holdings, sector_map, geo_map)
    """
    logger.debug(f"[{ticker}] Vanguard Playwright download interception: {url}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            f"[{ticker}] Playwright not installed. "
            "Run: pip install playwright && playwright install webkit"
        )
        return {}, {}, {}

    holdings: dict[str, float] = {}
    sectors: list[tuple[str, float]] = []
    geos: list[tuple[str, float]] = []

    import os
    import tempfile

    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.goto(url, timeout=45000)
            try:
                page.wait_for_selector("table", timeout=20000)
                page.wait_for_timeout(3000)
            except Exception:
                logger.debug(f"[{ticker}] Vanguard: page load timed out.")
                return {}, {}, {}

            # Click "Download all" and intercept the xlsx file
            try:
                with page.expect_download(timeout=20000) as download_info:
                    page.get_by_text("Download all").click()
                download = download_info.value
            except Exception as e:
                logger.debug(f"[{ticker}] Vanguard: download click failed: {e}")
                return {}, {}, {}

            # Save to temp file and parse
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                tmp_path = tmp_file.name
            try:
                download.save_as(tmp_path)
                # Dynamically find the header row (contains 'Holding Name')
                df_raw = pd.read_excel(tmp_path, engine="openpyxl", header=None)
                header_row = None
                for i, row in df_raw.iterrows():
                    vals = [str(v).strip() for v in row.values]
                    if "Holding Name" in vals or "Ticker" in vals:
                        header_row = i
                        break
                if header_row is None:
                    logger.debug(
                        f"[{ticker}] Vanguard: Could not find 'Holding Name' row in Excel."
                    )
                    return {}, {}, {}
                if not isinstance(header_row, int):
                    logger.debug(
                        f"[{ticker}] Vanguard: Found header row is not an integer: {header_row}"
                    )
                    return {}, {}, {}
                df = pd.read_excel(tmp_path, engine="openpyxl", header=header_row)
                df.columns = [str(c).strip() for c in df.columns]
            except Exception as e:
                logger.debug(f"[{ticker}] Vanguard: Excel parse failed: {e}")
                return {}, {}, {}
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            # Normalise column names
            col_map = {c.lower(): c for c in df.columns}
            name_col = next((col_map[k] for k in col_map if "holding" in k or "name" in k), None)
            weight_col = next((col_map[k] for k in col_map if "net assets" in k or "%" in k), None)
            sector_col = next((col_map[k] for k in col_map if "sector" in k), None)
            country_col = next((col_map[k] for k in col_map if "country" in k), None)

            if not name_col or not weight_col:
                logger.debug(
                    f"[{ticker}] Vanguard: Could not find Name/Weight cols. Cols={list(df.columns)}"
                )
                return {}, {}, {}

            for _, row in df.iterrows():
                name = str(row.get(name_col, "")).strip()
                weight_raw = str(row.get(weight_col, "")).replace("%", "").replace(",", "").strip()
                try:
                    weight = float(weight_raw)
                except ValueError:
                    continue
                if not name or name.lower() in ("nan", "") or weight <= 0:
                    continue

                holdings[name] = weight

                if sector_col:
                    sector = str(row.get(sector_col, "")).strip()
                    if sector and sector.lower() not in ("nan", ""):
                        sectors.append((sector, weight))
                if country_col:
                    country = str(row.get(country_col, "")).strip()
                    if country and country.lower() not in ("nan", ""):
                        geos.append((country, weight))

        except Exception as e:
            logger.debug(f"[{ticker}] Vanguard Playwright failed: {e}")
        finally:
            browser.close()

    return holdings, _aggregate_weights(sectors), _aggregate_weights(geos)


# ── Provider: Unknown — DDGS + Playwright fallback ────────────────────────────


def _discover_url_ddgs(ticker: str) -> str:
    """Tier 1.5: DuckDuckGo search for an ETF holdings page."""
    try:
        logger.debug(f"[{ticker}] DDGS URL discovery...")
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.text(f"{ticker} ETF portfolio holdings site:com.au OR site:com", max_results=5)
            )
            for res in results:
                href = res.get("href", "")
                if any(kw in href.lower() for kw in ["holdings", "portfolio", "fund"]):
                    return href
    except Exception as e:
        logger.debug(f"[{ticker}] DDGS discovery failed: {e}")
    return ""


def _fetch_playwright_generic(ticker: str, url: str) -> tuple[dict, dict, dict]:
    """Tier 2: Generic Playwright scrape for unknown providers."""
    if not url:
        return {}, {}, {}
    logger.debug(f"[{ticker}] Generic Playwright scrape: {url}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(f"[{ticker}] Playwright not installed.")
        return {}, {}, {}

    holdings: dict[str, float] = {}
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=30000)
            try:
                page.wait_for_selector("table", timeout=15000)
            except Exception:
                pass

            soup = BeautifulSoup(page.content(), "html.parser")
            tables = soup.find_all("table")

            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 5:
                    continue
                headers = [th.text.strip().lower() for th in rows[0].find_all(["th", "td"])]
                name_idx = next(
                    (
                        i
                        for i, h in enumerate(headers)
                        if any(x in h for x in ["name", "security", "holding", "issuer"])
                    ),
                    -1,
                )
                weight_idx = next(
                    (
                        i
                        for i, h in enumerate(headers)
                        if any(x in h for x in ["weight", "%", "portfolio"])
                    ),
                    -1,
                )
                if name_idx == -1 or weight_idx == -1:
                    continue

                table_holdings: dict[str, float] = {}
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) <= max(name_idx, weight_idx):
                        continue
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
            logger.debug(f"[{ticker}] Generic Playwright failed: {e}")
        finally:
            browser.close()

    return holdings, {}, {}


# ── Provider detection ────────────────────────────────────────────────────────


def _detect_provider(url: str) -> str:
    """Identify provider from URL."""
    if not url:
        return "unknown"
    url_lower = url.lower()
    if "betashares.com.au" in url_lower:
        return "betashares"
    if "globalxetfs.com.au" in url_lower:
        return "globalx"
    if "blackrock.com" in url_lower:
        return "blackrock"
    if "vanguard.com.au" in url_lower:
        return "vanguard"
    if "vaneck.com.au" in url_lower:
        return "vaneck"
    return "unknown"


# ── Main entry point ──────────────────────────────────────────────────────────

# ── User-managed URL store ────────────────────────────────────────────────────


def save_user_url(ticker: str, url: str) -> None:
    """
    Persist a user-provided fund page URL for a ticker.
    This URL takes precedence over PROVIDER_SEED_URLS in fetch_holdings.
    Clears the holdings cache so a fresh scrape is triggered on next fetch.
    """
    ticker = ticker.upper().replace(".AX", "")
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO etf_holdings_urls (ticker, url, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET url = excluded.url, updated_at = CURRENT_TIMESTAMP
            """,
            (ticker, url.strip()),
        )
        # Clear holdings cache so fresh scrape is triggered
        conn.execute(
            "DELETE FROM etf_metadata WHERE ticker = ? AND meta_type = 'holdings'",
            (ticker + ".AX",),
        )
        conn.execute("DELETE FROM etf_holdings_attempts WHERE ticker = ?", (ticker,))
        conn.commit()
        logger.info(f"[{ticker}] User URL saved: {url}")
    finally:
        conn.close()


def get_user_url(ticker: str) -> str:
    """Return the user-provided URL for a ticker, or empty string if none."""
    ticker = ticker.upper().replace(".AX", "")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT url FROM etf_holdings_urls WHERE ticker = ?", (ticker,)
        ).fetchone()
        return row["url"] if row else ""
    finally:
        conn.close()


def get_all_user_urls() -> dict[str, str]:
    """Return all user-provided ticker→URL mappings."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT ticker, url FROM etf_holdings_urls ORDER BY ticker").fetchall()
        return {r["ticker"]: r["url"] for r in rows}
    finally:
        conn.close()


# ── Main entry point ──────────────────────────────────────────────────────────


def fetch_holdings(ticker: str, allow_scrape: bool = False) -> dict:
    """
    Main entry point for fetching ETF holdings.
    Returns: { "Company Name": weight_percentage (0-100), ... }

    Args:
        ticker: The ticker symbol
        allow_scrape: If True, performs the scrape synchronously (for worker context).
                     If False, only returns cache or enqueues a background task.
    """
    ticker_yf = ticker.upper() + ".AX" if "." not in ticker else ticker.upper()
    ticker_short = ticker.upper().replace(".AX", "")

    # 1. Check SQLite cache first
    cached = _get_cached_metadata(ticker_yf, "holdings", ttl_days=HOLDINGS_TTL_DAYS)
    if cached:
        logger.debug(f"[{ticker_short}] Holdings cache hit ({len(cached)} entries).")
        return cached

    # 2. Check throttle — skip if we failed recently
    if _check_throttle(ticker_short):
        logger.debug(f"[{ticker_short}] Throttled — skipping fetch.")
        return {}

    # 3. If from Dash (allow_scrape=False), enqueue task and return empty
    if not allow_scrape:
        from data.database import enqueue_task, get_connection

        conn = get_connection()
        try:
            # Check if already enqueued
            row = conn.execute(
                "SELECT task_id FROM worker_tasks WHERE task_type = 'scrape_holdings' AND status IN ('pending', 'running') AND payload LIKE ?",
                (f'%"{ticker_short}"%',),
            ).fetchone()

            if not row:
                logger.info(f"[{ticker_short}] Enqueueing background holdings scrape.")
                enqueue_task("scrape_holdings", {"ticker": ticker_short}, priority=6)
        except Exception as e:
            logger.error(f"[{ticker_short}] Failed to enqueue holdings scrape: {e}")
        finally:
            conn.close()
        return {}

    # 4. Determine URL: user-provided → PROVIDER_SEED_URLS → empty
    user_url = get_user_url(ticker_short)
    url = user_url or PROVIDER_SEED_URLS.get(ticker_short, "")
    provider = _detect_provider(url)

    holdings: dict[str, float] = {}
    sector_map: dict[str, float] = {}
    geo_map: dict[str, float] = {}

    # 5. Tier 1 — Provider-specific scrape
    if provider == "betashares":
        holdings, sector_map, geo_map = _fetch_betashares(ticker_short, url)

    elif provider == "globalx":
        holdings, sector_map, geo_map = _fetch_globalx(ticker_short, url)

    elif provider == "blackrock":
        holdings, sector_map, geo_map = _fetch_blackrock(ticker_short, url)

    elif provider == "vaneck":
        holdings, sector_map, geo_map = _fetch_vaneck(ticker_short, url)

    elif provider == "vanguard":
        holdings, sector_map, geo_map = _fetch_vanguard_playwright(ticker_short, url)

    # 6. Tier 1.5 + Tier 2 — Unknown provider or Tier 1 failed
    discovered_url = ""
    if not holdings and provider == "unknown":
        discovered_url = _discover_url_ddgs(ticker_short)
        target_url = discovered_url or url
        if target_url:
            holdings, sector_map, geo_map = _fetch_playwright_generic(ticker_short, target_url)

    # 7. Normalise
    holdings = _normalize_holdings(holdings)

    # 7. Persist to cache or record failure
    if holdings:
        _save_metadata(ticker_yf, "holdings", holdings)
        _save_sector_geo_from_holdings(ticker_yf, sector_map, geo_map)
        _clear_throttle(ticker)
        logger.info(
            f"[{ticker}] Fetched {len(holdings)} holdings via '{provider}'. "
            f"Sector: {len(sector_map)} cats, Geo: {len(geo_map)} regions."
        )
        # Auto-persist discovered URL to etf_holdings_urls table
        if discovered_url:
            try:
                conn = get_connection()
                try:
                    conn.execute(
                        """
                        INSERT INTO etf_holdings_urls (ticker, url, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(ticker) DO UPDATE SET url = excluded.url, updated_at = CURRENT_TIMESTAMP
                        """,
                        (ticker_short, discovered_url),
                    )
                    conn.commit()
                    logger.info(f"[{ticker_short}] Discovered URL saved to DB: {discovered_url}")
                finally:
                    conn.close()
            except Exception as ex:
                logger.error(f"[{ticker_short}] Failed to save discovered URL: {ex}")
    else:
        _record_attempt(ticker, f"Failed all tiers (provider={provider})")
        logger.warning(f"[{ticker}] All fetch strategies failed.")

    return holdings
