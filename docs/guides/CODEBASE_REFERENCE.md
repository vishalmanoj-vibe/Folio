# Folio Codebase Reference & Architecture Directory

This reference document outlines the core structural components of the Folio Portfolio Dashboard codebase. It defines the target pages and single primary functions of all callbacks, details the precise data fetched and computed by all backend services, and catalogs the highly protected files that should never be edited.

---

## 📞 Callbacks Directory (`callbacks/`)

Each callback module operates under a thin orchestration paradigm, containing zero math or business logic, and delegates all computations to underlying service/engine components.

| File Name | Target Page / Element | The One Thing It Does |
| :--- | :--- | :--- |
| **`alert_callbacks.py`** | Global header banner & alerts badge | Scans current holdings data to render warning banners and update the global intelligence notification count. |
| **`chart_callbacks.py`** | Dashboard Home (`/`) & Analytics (`/analytics`) | Renders and updates all core statistical figures (P&L history, normalized price comparison, sector/geo treemaps, volatility, correlation heatmaps, and ETF underlying holdings treemaps) and configures fund URL paths. |
| **`intelligence_callbacks.py`** | Portfolio Intelligence (`/intelligence`) | Computes portfolio-wide risk ratios (volatility, Sharpe, drawdowns), renders the equity curve (including ML prediction overlays), and generates optimization alerts. |
| **`portfolio_callbacks.py`** | Dashboard Home (`/`) | Updates global portfolio stats and renders the primary sortable, filterable holdings table containing color-coded AI recommendation badges. |
| **`positions_callbacks.py`** | Positions & Dividends (`/positions`) | Manages the interactive sidebar holding cards (with sparklines), details selected assets, renders Candlestick history, and displays individual/portfolio dividend metrics. |
| **`research_callbacks.py`** | Floating AI Chatbot & Reports | Coordinates the global floating AI chatbot widget drawer (message sending, streaming, quick prompts context, usage limits), tracks rate limits, and coordinates weekly PDF report generation and downloads. |
| **`setup_callbacks.py`** | Onboarding Wizard (`/setup/*`) | Guides new users through transaction logging, Gemini API configuration, writes onboarding states to the database, and schedules initial data refreshes. |
| **`signals_callbacks.py`** | Signals Generation (Global Header) | Manages manually triggered technical signal generation, enqueues worker tasks, monitors queue status, and updates header generation status markers. |
| **`transaction_callbacks.py`** | Transaction Ledger | Controls the manual transaction addition ledger form, auto-discovers ticker names and current prices, and refreshes the transaction history tables. |
| **`ui_callbacks.py`** | Global Interface Interactions | Controls theme state toggles, coordinates clientside theme switches and print triggers, highlights active nav links, and manages manual data refreshes. |
| **`watchlist_callbacks.py`** | Watchlist (`/watchlist`) | Drives watchlist card lists, rendering interactive pricing tables, managing ticker additions and removals, plotting custom price ranges, and displaying technical indicators. |

---

## ⚙️ Services & Market Directory (`services/` & `services/market/`)

Backend services represent the business logic and core mathematical engines. They are pure Python components and never import from Dash or frontend layout scripts.

### Core Services (`services/`)

*   **`ai_engine.py`**
    *   *Data Fetched/Computed:* Passes technical score signals to the Gemini API (`gemini-3.1-flash-lite`) to construct qualitative investment critiques, list structural asset risks, and normalize confidence verdicts.
    *   *Rules:* Low-conviction signals (score `< 0.4`) are ignored to limit API costs. Leverages 24-hour deterministic caching based on rounded signal inputs.
*   **`alert_service.py`**
    *   *Data Fetched/Computed:* Scans enriched holdings cost bases to calculate drawdown percentages. Triggers individual alerts below `-20%` and total portfolio alerts below `-15%` relative to initial costs.
*   **`history_cache.py`**
    *   *Data Fetched/Computed:* **DEPRECATED.** Previously cached historical arrays in RAM. Modified to return empty values to prevent memory leaks and force downstream components to query SQLite directly.
*   **`intelligence_service.py`**
    *   *Data Fetched/Computed:* Computes complex portfolio performance arrays. Aggregates sector and geographic asset allocation maps, calculates historical drawdown curves, and processes rolling volatility arrays.
*   **`prediction_service.py`**
    *   *Data Fetched/Computed:* Generates forward-looking return forecasts (using the Facebook Prophet model). Downsamples datasets to a maximum of 500 points for performance, applies Australian holiday constraints, and computes continuity corrections to align predictions with last-traded closes.
*   **`report_service.py`**
    *   *Data Fetched/Computed:* Orchestrates the compilation of weekly PDF portfolio summaries. Discovers upcoming dividend payouts, fetches recent financial news and general ASX headlines, generates Gemini market outlook commentary, plots matplotlib P&L trend charts, and assembles components into an A4 document.
*   **`research_memory.py`**
    *   *Data Fetched/Computed:* Manages the persistence of chat histories. Enforces a 7-day conversation pruning limit, compresses old dialog turns into persistent summaries via AI, and monitors file size thresholds (50MB capacity cap) to prevent storage bloat.
*   **`research_service.py`**
    *   *Data Fetched/Computed:* Backend engine for the AI Analyst chat. Prepares condensed portfolio context (top 20 holdings and recent technical indicators) to prevent context overflows, intercepts chat prompts to run real-time web searches, and handles model exchanges with Gemini.
*   **`strategy_engine.py`**
    *   *Data Fetched/Computed:* Evaluates historical price arrays against a weighted quantitative model to yield standard recommendations. Calculates weights across five parameters: Trend (50MA vs 200MA - 0.35), Momentum (RSI - 0.20), Price vs 200MA (0.15), Price vs Cost (0.15), and Drawdown (0.15).
    *   *Rules:* BUY >= 0.5, SELL <= -0.5, else HOLD. Applies hysteresis (prevents flip-flopping if new score is `< 0.7`) and appends Capital Gains Tax (CGT) warnings if a sold tranche has been held under 1 year.
*   **`technical_indicators.py`**
    *   *Data Fetched/Computed:* Computes standard technical mathematical arrays using pure pandas logic (no external TA libraries). Computes Relative Strength Index (Wilder's smoothed RSI), MACD lines and signal crossovers, standard 20-period Bollinger Bands, SMA 200 trends, and 30-day historical volatility.
*   **`web_search.py`**
    *   *Data Fetched/Computed:* Scrapes regional DuckDuckGo indexes to fetch recent financial announcements and ticker-specific headlines. Contains heuristic keywords to determine if user chat queries require real-time search supplementation.

### Market Services (`services/market/`)

*   **`data_fetcher.py`**
    *   *Data Fetched/Computed:* Manages high-performance Yahoo Finance bulk downloads. Computes realized dividends (ex-dividend schedules mapped against tranche purchase timestamps), filters session open/close boundaries, triggers concurrent holding data enrichments, and maintains caching under a 290s cooldown to prevent throttling.
*   **`dividend_service.py`**
    *   *Data Fetched/Computed:* Centralizes and evaluates all dividend metrics. Gathers raw payout dates and distributions, aggregates cost-basis yields and annual cash projections, deduces median pay frequencies, and maps ex-dividend schedules into chronological upcoming event calendars.
*   **`holdings_fetcher.py`**
    *   *Data Fetched/Computed:* Scrapes and compiles underlying ETF asset allocations (company weights, sectors, and geographies). Operates a robust multi-strategy parser (direct static HTML parsing for BetaShares/Global X, AJAX CSV extraction for BlackRock, API URL discovery for VanEck, and Playwright WebKit SPA download interception for Vanguard).
*   **`market_status.py`**
    *   *Data Fetched/Computed:* Computes local timezone context (`Australia/Sydney` business days and holidays). Evaluates if active trading is underway, computes trading sessions starts (e.g. 15:00 lookbacks for daily charts), and returns sleep durations until the next market opening.
*   **`session_cache.py`**
    *   *Data Fetched/Computed:* Records and backfills intraday price points into SQLite cache tables during active market sessions. Limits storage growth by automatically deleting intraday logs older than 2 days.

---

## 🔒 Protected Codebase Files — NEVER Edit Without Explicit Instruction

These files define core structural routing, schemas, and layouts, or represent the unified logic standard. Editing them without absolute care will break the application's multi-page coordination, relational constraints, or scoring integrity.

### 1. `app.py`
*   *Why:* It acts as the application's entrypoint, instantiating the Dash app context and seeding the global `dcc.Store` memory slots (`txn-store` and `portfolio-store`). Modifying its layout or key memory nodes disrupts data propagation to all downstream sub-pages and causes major rendering faults.

### 2. `data/portfolio.db`
*   *Why:* The centralized SQLite database that serves as the single source of truth for transactions, watchlists, cache markers, and user data. Never attempt to manually override or delete the database file; any changes to schemas must occur programmatically.

### 3. `services/strategy_engine.py`
*   *Why:* Enforces the core rule-based system for buy/sell/hold signal scores. Strategy calculations are mathematical, deterministic, and highly curated; they must never be altered or overwritten by AI output.

### 4. `services/ai_engine.py`
*   *Why:* Coordinates the Gemini AI Analyst review. It is explicitly designed to sit *after* the strategy engine to critique and explain, never to override signals. It holds critical verdict normalizations and tone sanitizations to ensure financial safety.

### 5. `services/market/dividend_service.py`
*   *Why:* Serves as the single centralized logical layer for all dividend calculations, eligibility schedules, and projections. Any modification can cause major inaccuracies in overall portfolio statistics or calendar errors.
