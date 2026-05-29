# Skill: External Data Fetching & Scraping
**File:** `.agents/skills/data_fetching.md`
**Applies to:** Any feature involving network requests, external APIs, web scraping, or provider data ingestion.

---

## 1. Core Rules (Never Break These)

- **No hardcoded external URLs without verification.** Every URL used in production code must return a valid HTTP 200 before being committed. If a URL cannot be verified at build time, implement the DDGS discovery fallback (see Section 3).
- **Never use `requests` alone for JS-rendered pages.** Provider sites (BetaShares, BlackRock, VanEck) render holdings tables via JavaScript. `requests` + BeautifulSoup will return empty HTML. Always use the three-tier pattern.
- **Return `None` on failure, never `{}`.**  The calling service must be able to distinguish "scrape failed" from "provider has no data". An empty dict `{}` is ambiguous. `None` is unambiguous failure.
- **Never reimplement SQLite write logic in a fetcher.** Use `_save_metadata()` and `_get_cached_metadata()` from `intelligence_service.py`. Do not duplicate persistence logic.
- **No `print()` statements in fetchers.** Use `logger.debug/info/warning/error` only. Follows the project-wide no-print rule in `GEMINI.md`.

---

## 2. Three-Tier Scraping Pattern

All external data fetching must follow this exact tier order. Do not skip tiers.

```
fetch_holdings(ticker)
    │
    ├── Tier 1: Direct CSV/JSON API via requests
    │       → If returns valid dict with 5+ entries: store in SQLite, return
    │       → If fails or returns < 5 entries: fall through to Tier 1.5
    │
    ├── Tier 1.5: DDGS URL Discovery
    │       → Search: "{ticker} ASX ETF holdings site:{provider_domain}"
    │       → 5-second timeout — return hardcoded fallback URL silently on failure
    │       → Pass discovered URL to Tier 2
    │
    ├── Tier 2: Playwright WebKit headless browser
    │       → Navigate to URL (30s timeout)
    │       → Wait for table selector (15s timeout)
    │       → Click "View All" / "Show All Holdings" if present
    │       → Extract rendered HTML → BeautifulSoup
    │       → Find table with most rows
    │       → Parse into {company_name: weight_pct}
    │       → If returns valid dict: store in SQLite, return
    │       → If fails: record in etf_holdings_attempts, return None
    │
    └── All tiers failed → return None
```

---

## 3. DDGS URL Discovery

Use the existing `ddgs` package (already in `requirements.txt`) for self-healing URL mapping.

```python
from ddgs import DDGS

def _discover_url(ticker: str, provider_domain: str) -> str | None:
    """Search DuckDuckGo for the current holdings page URL."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                f"{ticker} ASX ETF holdings {provider_domain}",
                max_results=3,
                timelimit="y"  # Last year only
            )
            for r in results:
                href = r.get("href", "")
                if provider_domain in href and "holding" in href.lower():
                    return href
    except Exception as e:
        logger.warning(f"DDGS URL discovery failed for {ticker}: {e}")
    return None  # Caller falls back to hardcoded URL
```

**Rules:**
- Always wrap in try/except — DDGS failure must never block the scrape
- 5-second implicit timeout via max_results=3 (fast query)
- Validate result contains both the provider domain AND "holding" in the URL
- Log at WARNING level if DDGS fails, not ERROR — it's a non-critical fallback

---

## 4. Playwright WebKit Rules

**Always use WebKit, not Chromium or Firefox.**
WebKit matches the Safari rendering engine used to view the dashboard and is lighter (~80MB vs ~150MB for Chromium).

```python
from playwright.sync_api import sync_playwright

def _scrape_with_playwright(url: str, ticker: str) -> dict | None:
    """Shared Playwright WebKit scraper for all providers."""
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                              "Version/17.0 Safari/605.1.15"
            })
            page.goto(url, timeout=30000)

            try:
                page.wait_for_selector("table", timeout=15000)
            except Exception:
                logger.warning(f"{ticker}: No table found after 15s on {url}")
                return None

            # Click "View All" / "Show All" if present
            for btn_text in ["View All", "Show All", "Show all holdings", "Load more"]:
                try:
                    btn = page.get_by_text(btn_text, exact=False)
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            html = page.content()
            return _parse_holdings_from_html(html, ticker)

    except Exception as e:
        logger.error(f"{ticker}: Playwright scrape failed for {url}: {e}")
        return None
    finally:
        # CRITICAL: Always close browser — leaked processes slow down the Mac
        if browser:
            browser.close()
```

**Rules:**
- `try/finally` with `browser.close()` is mandatory — never omit
- Always set a Safari-matching User-Agent — WebKit without a UA gets blocked
- `goto` timeout: 30 seconds
- `wait_for_selector` timeout: 15 seconds
- Never launch more than one browser instance at a time
- `headless=True` always — never open a visible window in background tasks

---

## 5. HTML Table Parsing (Provider-Agnostic)

Use a single shared parsing function for all providers. Do not write separate parsers per provider.

```python
from bs4 import BeautifulSoup

def _parse_holdings_from_html(html: str, ticker: str) -> dict | None:
    """Extract holdings from rendered HTML. Provider-agnostic."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        logger.error(f"{ticker}: No tables found in rendered HTML")
        logger.debug(f"{ticker} HTML preview: {html[:500]}")
        return None

    # Use the table with the most rows — usually the holdings table
    best_table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = best_table.find_all("tr")

    result = {}
    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue

        name = cells[0]
        weight_str = next(
            (c for c in cells[1:] if "%" in c),
            None
        )

        # Skip invalid rows
        if not weight_str:
            continue
        if _is_date(name) or not name or len(name) < 2:
            continue

        try:
            weight = float(weight_str.replace("%", "").replace(",", "").strip())
            if not (0.01 <= weight <= 100):
                continue
            result[name] = round(weight, 4)
        except ValueError:
            continue

    if len(result) < 5:
        logger.error(f"{ticker}: Only {len(result)} valid rows parsed — likely wrong table")
        logger.debug(f"{ticker} HTML preview: {html[:500]}")
        return None

    # Always append Other residual
    total = sum(result.values())
    if total < 99:
        result["Other"] = round(100 - total, 2)

    logger.info(f"{ticker}: parsed {len(result)} holdings successfully")
    return result


def _is_date(text: str) -> bool:
    """Returns True if text looks like a date string."""
    import re
    return bool(re.match(
        r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$|^\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}$",
        text.strip()
    ))
```

---

## 6. HTTP Request Headers

All `requests` calls to external providers must include these headers:

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                  "Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.google.com/",
}
```

Never make a bare `requests.get(url)` without headers — provider sites block requests without a User-Agent.

---

## 7. SQLite Persistence Pattern

After any successful scrape, store results immediately. Use existing helpers — do not reimplement.

```python
from services.intelligence_service import _save_metadata, _get_cached_metadata

# Check cache first (30-day TTL for holdings)
cached = _get_cached_metadata(ticker_yf, "holdings")
if cached:
    return cached

# After successful scrape:
_save_metadata(ticker_yf, "holdings", result)
```

**TTL Reference:**
| Data Type | TTL | Rationale |
|---|---|---|
| Holdings | 30 days | Providers rebalance monthly at most |
| Sector weights | 7 days | More volatile, matches existing pattern |
| Geo weights | 7 days | More volatile, matches existing pattern |

---

## 8. Retry Throttling

Failed scrapes must be recorded to prevent repeated attempts on every startup.

**Table:** `etf_holdings_attempts (ticker TEXT PRIMARY KEY, last_attempt TEXT, last_error TEXT)`

**Logic:**
```python
# Before scraping — check throttle
conn = get_connection()
row = conn.execute(
    "SELECT last_attempt FROM etf_holdings_attempts WHERE ticker = ?", 
    (ticker,)
).fetchone()

if row:
    last = pd.to_datetime(row["last_attempt"])
    if (pd.Timestamp.now() - last).total_seconds() < 86400:  # 24 hours
        logger.debug(f"{ticker}: Scrape throttled — last attempt {last}")
        return None

# After failure — record attempt
conn.execute(
    """INSERT INTO etf_holdings_attempts (ticker, last_attempt, last_error)
       VALUES (?, CURRENT_TIMESTAMP, ?)
       ON CONFLICT(ticker) DO UPDATE SET 
           last_attempt = CURRENT_TIMESTAMP, last_error = ?""",
    (ticker, str(error), str(error))
)
conn.commit()
```

---

## 9. Provider URL Registry

Maintain this mapping in `holdings_fetcher.py` as `PROVIDER_URLS`. Update when URLs change — do not scatter URLs throughout the file.

```python
PROVIDER_URLS = {
    "VHY":  {
        "provider": "vanguard",
        "domain": "vanguard.com.au",
        "tier1": "https://www.vanguard.com.au/personal/api/fund/holdings?portId=8149",
        "tier2": "https://www.vanguard.com.au/personal/invest-with-us/fund?id=8149",
    },
    "IOZ":  {
        "provider": "blackrock",
        "domain": "blackrock.com/au",
        "tier1": "https://www.ishares.com/au/individual/en/products/251789/fund.ajax?fileType=csv&dataType=fund",
        "tier2": "https://www.blackrock.com/au/individual/products/251789/",
    },
    "IOO":  {
        "provider": "blackrock",
        "domain": "blackrock.com/au",
        "tier1": "https://www.ishares.com/au/individual/en/products/237666/fund.ajax?fileType=csv&dataType=fund",
        "tier2": "https://www.blackrock.com/au/individual/products/237666/",
    },
    "AINF": {
        "provider": "betashares",
        "domain": "betashares.com.au",
        "tier1": None,
        "tier2": "https://www.betashares.com.au/fund/aims-global-infrastructure-etf/",
    },
    "ASIA": {
        "provider": "betashares",
        "domain": "betashares.com.au",
        "tier1": None,
        "tier2": "https://www.betashares.com.au/fund/asia-technology-tigers-etf/",
    },
    "SEMI": {
        "provider": "betashares",
        "domain": "betashares.com.au",
        "tier1": None,
        "tier2": "https://www.betashares.com.au/fund/global-semiconductor-etf/",
    },
    "XMET": {
        "provider": "betashares",
        "domain": "betashares.com.au",
        "tier1": None,
        "tier2": "https://www.betashares.com.au/fund/energy-transition-metals-etf/",
    },
    "QUAL": {
        "provider": "vaneck",
        "domain": "vaneck.com.au",
        "tier1": "https://www.vaneck.com.au/globalassets/fund-data/qual/holdings.json",
        "tier2": "https://www.vaneck.com.au/etf/equity/qual/holdings/",
    },
}
```

**Adding a new ETF:** Add one entry to this dict. If the provider is already supported, nothing else changes. If it's a new provider, add a provider-specific Tier 1 function and map it in `PROVIDER_REGISTRY`.

---

## 10. Logging Standards

Every scraper function must log at these levels:

| Event | Level | Example |
|---|---|---|
| Tier 1 success | INFO | `"VHY: Tier 1 CSV parsed 52 holdings"` |
| Tier 1 failure, trying 1.5 | WARNING | `"VHY: Tier 1 failed (404), trying DDGS discovery"` |
| DDGS found URL | INFO | `"VHY: DDGS discovered URL: https://..."` |
| DDGS failed | WARNING | `"VHY: DDGS discovery failed — using hardcoded URL"` |
| Tier 2 success | INFO | `"VHY: Tier 2 Playwright parsed 52 holdings"` |
| Tier 2 HTML loaded but 0 rows | ERROR | `"VHY: 0 rows parsed — check table selector"` + DEBUG html preview |
| All tiers failed | ERROR | `"VHY: All tiers failed — recording attempt"` |
| Throttled | DEBUG | `"VHY: Scrape throttled — last attempt 3h ago"` |
| Cache hit | DEBUG | `"VHY: Returning cached holdings (12 days old)"` |

---

## 11. Installation Requirements

Playwright requires a one-time manual install step after `pip install playwright`:

```bash
playwright install webkit
```

This must be documented in:
- `requirements.txt` — add `playwright>=1.40.0`
- `GEMINI.md` — add under Setup section
- The Stage 4 build report — flag as a manual step for any new environment

**Never add `os.system("playwright install webkit")` to application code.** This is a developer setup step only.

---

## 12. Isolation Test Command

Run this after any scraper change before testing the UI:

```bash
python -c "
from services.market.holdings_fetcher import fetch_holdings
for ticker in ['VHY', 'IOZ', 'IOO', 'AINF', 'ASIA', 'SEMI', 'XMET', 'QUAL']:
    result = fetch_holdings(ticker)
    print(f'{ticker}: {len(result) if result else 0} holdings — {list(result.items())[:2] if result else \"EMPTY\"}')
" 2>&1
```

**Pass criteria:** Every ticker returns at least 5 holdings with string keys and float values between 0 and 100. Any `EMPTY` result is a failure that must be fixed before UI testing.