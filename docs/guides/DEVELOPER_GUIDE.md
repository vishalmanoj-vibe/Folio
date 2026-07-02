# Developer Guide & Architecture Overview

This document outlines the architecture, layer model, and data flow of the Folio Dashboard.

### Layer Model

The application follows a strictly decoupled layered architecture to ensure separation of concerns. A key distinction is the separation of **Market Services** (orchestration/network) from the **Engine** (pure math/logic).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION LAYER                              │
│  (app.py, launcher.py, pages/, callbacks/, components/, assets/)             │
└──────────┬───────────────────────────┬───────────────────────┬──────────────┘
           │                           │                       │
           ▼                           ▼                       ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│     SERVICE LAYER     │   │      ENGINE LAYER     │   │    DATA ACCESS LAYER  │
│ (market, intelligence,│   │ (core/engine/         │   │ (data/repository.py,  │
│  research, strategy)  │   │  portfolio_engine.py, │   │  data/database.py)    │
│                       │   │  stats_engine.py)     │   │                       │
└──────────┬────────────┘   └───────────┬───────────┘   └───────────┬───────────┘
           │                            │                           │
           ▼                            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│      DOMAIN LAYER     │   │   FOUNDATION LAYER    │   │  BACKGROUND WORKER    │
│ (models/transaction.py)    │   (core/, config/)    │   │ (worker.py, tasks/)   │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

### Layer Responsibilities

1.  **Presentation (UI/Assets)**: The entry point and orchestrator. It handles the "Shell" (HTML/CSS), multi-page routing, and interactive state (`dcc.Store`). It coordinates the flow by loading raw transactions from the **Data Layer** and passing them to the **Service Layer** for enrichment.
2.  **Service (Orchestration & Intelligence)**: Coordinates complex workflows and AI-driven insights. This layer handles external API calls (yfinance, Gemini), tiered caching, and logic-heavy services:
    - **Market Service**: Real-time pricing and metadata enrichment.
    - **Dividend Service**: Centralized logic for realized income, trend analysis, and projected distributions.
    - **Research Service (AI)**: Contextual portfolio reasoning via Gemini 2.5 Flash.
    - **Web Search Service**: Live financial news integration via DuckDuckGo.
    - **Memory Service**: Persistent state management with rolling 7-day logs and long-term summaries.
    - **Intelligence Service**: Risk analysis (Sharpe, Volatility) and rule-based allocation alerts.
    - **Prediction Service**: Forecasting using Facebook Prophet with continuity correction.
3.  **Engine (Logic)**: The "Mathematical Core". Pure Python logic for P&L computation, tranche aggregation, and performance metrics.
    - **Portfolio Engine**: Core aggregation and tranche history logic.
    - **Stats Engine**: High-performance formatting and summary aggregation for UI consumption.
    - **Zero dependencies** on Network, I/O, or Dash.
4.  **Data (Persistence)**: The `PortfolioRepository` and `WatchlistRepository` provide a clean abstraction for data operations. The system uses a **Relational SQLite** backend (`portfolio.db`) for all state data (Transactions, Watchlist, Metadata), utilizing WAL mode for concurrency. JSON is retained only for transient intraday snapshots.
5.  **Domain (Models)**: Typed definitions (Pydantic/TypedDict) that enforce data contracts across all layers.
6.  **Foundation (Core/Config)**: System-wide utilities (Validators, TTL Caching, Logging) and environment configuration.
7.  **Background Worker**: A separate process (`worker.py`) that handles I/O-bound and CPU-intensive tasks (Technical Signals, ETF Scrapes, Market Refreshes).

---

## Distributed Intelligence & Memory Hygiene

To maintain a lightweight memory footprint (~300MB baseline) and prevent UI freezes, Folio uses a distributed task architecture.

### 1. The Worker Process (`worker.py`)
The worker process is the "heavy lifter". It handles:
- **`generate_signals`**: Computes RSI/MACD and runs AI signal analysis.
- **`scrape_holdings`**: Executes Playwright-based browser sessions to discover ETF holdings.
- **`fetch_history`**: Backfills missing market data for new tickers.
- **`maintenance`**: Cleans up old caches and summarizes AI memory.

### 2. Task Orchestration
The Dash UI never executes heavy scrapers directly. Instead, it uses `enqueue_task()` to signal the worker.
- **Enqueuing**: `services/market/holdings_fetcher.py` checks if data is missing; if so, it adds a `scrape_holdings` task to the SQLite queue.
- **UI State**: The dashboard displays "Scraping in progress..." or "Loading signals..." while the worker is busy.

### 3. Memory Safeguards
- **Staleness Gating**: A strict 24-hour gate prevents redundant historical fetches.
- **Smart Depth Awareness**: Prevents infinite loops for young tickers (listed < 220 days) by tracking the history period in metadata.
- **Metadata Truncation**: Strips unused fields from yfinance objects before database insertion.

---

## Data Consistency (OHLC & P&L)
To ensure visual and mathematical consistency across the dashboard, the system uses `auto_adjust=True` for all historical market data fetching.
- **Why**: Standardizing on adjusted prices prevents "dividend drops" from appearing as artificial price crashes in Candlestick charts and prevents false signals in Technical Indicators (RSI/MACD).
- **Impact**: All historical OHLC values (Open, High, Low, Close) are adjusted proportionally to reflect corporate actions and dividends.
- **Limitation**: While this is ideal for performance visualization, it may cause a mismatch if comparing adjusted historical prices to raw historical purchase prices for very old transactions in stocks that have split. (Rare for ASX ETFs).

---

### 1. Startup Hydration (app.py)
To ensure a premium "instant-on" experience, the dashboard uses a **Fast-Startup** pattern:
1.  **Fast Load**: `load_portfolio_snapshot()` reads the last known good state from disk.
2.  **Seed**: `dcc.Store` is initialized with this cached data. The app becomes interactive in <1s.
3.  **Deferred Refresh**: A `startup-interval` (1.5s delay) triggers the first live fetch.
4.  **Background Maintenance**: A background thread maintains 5-minute snapshots in `data/cache/` during market hours to ensure chart continuity.

### 2. Reactivity Loop
Once running, the dashboard follows a **Single Refresh Owner** pattern:
- **`update_txn_store`**: The exclusive writer for transaction data.
- **`update_portfolio_store`**: The exclusive caller of `fetch_live()`. It reacts to transaction changes or interval ticks.
- **Prioritized Rendering**: To prevent UI flicker, callbacks check `pathname` and return `dash.no_update` if their page is not visible. (See Section 16).

### 3. Multi-Tier Interval Strategy
To balance UI responsiveness with network efficiency, the application uses multiple `dcc.Interval` components:
- **Heartbeat (`live-interval` & `heartbeat-interval`, 30s)**: Drives UI-only updates like market status badges and time-ago counters without making network requests.
- **Data Refresh (`price-interval`, 300s)**: Triggers periodic data fetches (e.g., `update_portfolio_store` and `update_watchlist_store`).
- **Market Gating**: The `price-interval` is gated by `is_market_open()`. If the market is closed, periodic fetches are skipped, preventing redundant network calls while keeping the UI responsive to manual actions.

---

## Relational Database & Concurrency

The application utilizes a robust relational structure in **SQLite** to manage identity and state.

### 1. Concurrency Model (WAL)
To prevent "Database Locked" errors when the background snapshot thread writes while the Dash UI reads, the database is configured with:
- **Journal Mode**: `WAL` (Write-Ahead Logging).
- **Synchronous**: `NORMAL`.
- **Busy Timeout**: `5000ms`.
This enables multiple readers and one writer to coexist safely.

### 2. Schema Overview
- **`transactions`**: Historical buys/sells.
- **`assets`**: Persistent cache for ticker names and categories (lazy-loaded via `get_etf_name`).
- **`watchlist`**: Ticker membership, custom sorting order (`order_index`), and merged notes.
- **`etf_metadata`**: Blended sector/geographic weights.

### 3. Persistent Metadata Caching
ETF metadata (Sector/Geo) is stored in the `etf_metadata` table.
- **Stale Check**: The `intelligence_service` implements a **7-day stale check** (`updated_at`).
- **Efficiency**: Reduces redundant yfinance API calls by 95% for existing holdings.

---

## Global State Management

The application utilizes a sophisticated `dcc.Store` ecosystem to manage state across multiple pages without expensive re-fetches.

### 1. The Portfolio Store (`portfolio-store`)
- **Role**: The single source of truth for all holding data, histories, and metrics.
- **Hydration**: Pre-seeded at startup in `app.py` to ensure instantaneous first-paint.
- **Reactivity**: Updated every 300s (via `live-interval` defined in `config/settings.py`) or immediately upon transaction entry.

### 2. Preference & Session Stores
- **`theme-store`**: Local storage persistence for light/dark mode preference.
- **`period-store` / `pnl-mode-store`**: Session storage persistence for user selections (Timeframe, $ vs %), ensuring selections persist when navigating between pages.
- **`positions-selected-ticker`**: Tracks the active ticker for the deep-dive panel on the Positions page.
- **`positions-period-store`**: Positions chart period selection.
- **`watchlist-selected-ticker`**: Tracks selected ticker on Watchlist.
- **`watchlist-period-store`**: Watchlist chart period selection.

### 3. UI Context Stores
- **`nav-link-store`**: Dynamically updates the header badges by listening to URL path changes.
- **`compact-mode-store`**: Controls the density of the main portfolio table.
- **`research-usage-store`**: Persistent counter for Gemini API usage, reset daily.

---

## Technical Constraints & Algorithms

For specific mathematical formulas, visual standardization, custom chart helpers, and detailed specialized algorithms, refer to:
*   **[ALGORITHMS_AND_FEATURES.md](ALGORITHMS_AND_FEATURES.md)**: Standardized Plotly chart layouts, realized dividend calculations, FB Prophet continuity offset, and custom HTML5 drag-and-drop mechanics.
*   **[GEMINI.md](../../GEMINI.md)**: Coding rules, architecture constraints, and AI agent boundaries.

---

## Related Documentation

For non-architectural details, please refer to:
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Setup instructions, environment configuration, and how to add new features.
- **[TESTING.md](../testing/TESTING.md)**: Manual verification steps and automated test suite status.

---

## Directory Structure

```
folio/
├── app.py                          # Entry point (Seeds stores + defines refresh loop)
│
├── config/                         # Configuration layer (Settings, Constants)
│   ├── settings.py                 # Settings + env vars (Refresh rates, cache TTLs, DB path)
│   ├── constants.py                # Colors, static names, themes
│   └── logging.py                  # Logging configuration
│
├── core/                           # Foundation layer
│   ├── engine/                     # Pure logic (Math, Aggregation)
│   │   ├── portfolio_engine.py     # Aggregation & Tranche history
│   │   ├── stats_engine.py         # Summary metrics & UI formatting
│   │   └── utils.py                # Math helpers
│   ├── cache.py                    # TTL cache for API responses
│   └── validators.py               # Transaction schema validation
│
├── models/                         # Domain layer
│   └── transaction.py              # Holding & Transaction schemas
│
├── services/                       # Orchestration layer
│   ├── market/                     # Network calls (yfinance)
│   │   ├── data_fetcher.py         # Enrichment logic (Bulk Fetch)
│   │   ├── dividend_service.py     # Realized Dividends & Trend logic
│   │   ├── session_cache.py        # Intraday snapshot management
│   │   └── market_status.py        # ASX timezone/status logic
│   ├── ai_engine.py                # LLM orchestration & signal critique
│   ├── strategy_engine.py          # Deterministic rule-based scoring
│   ├── alert_service.py            # Price/Target monitoring
│   ├── intelligence_service.py     # Hierarchical risk/allocation logic
│   ├── prediction_service.py       # Prophet-based forecasting
│   ├── report_service.py           # Weekly PDF generation
│   ├── research_service.py           # AI Assistant (chat & web search)
│   └── research_memory.py          # Persistent AI memory summaries
│
├── data/                           # Persistence layer
│   ├── database.py                 # SQLite connection & schema (WAL enabled)
│   ├── repository.py               # Transaction & Asset Repository
│   ├── watchlist_repository.py     # Watchlist & History Repository
│   ├── portfolio.db                # Main relational store
│   └── cache/                      # Persistent disk cache (intraday snapshots)
│
├── components/                     # UI components
│   ├── charts/                     # go.Figure factories
│   │   ├── helpers.py              # Centralized layout & empty state builders
│   │   ├── pnl_history.py          # Today view (resampled)
│   │   ├── price_history.py        # Candlestick/Line charts
│   │   └── ...
│   ├── header.py                   # Shared navigation header
│   ├── ui_helpers.py               # Stat cards & section wrappers
│   └── chatbot.py                  # Floating AI Assistant widget layout
│
├── callbacks/                      # Dash interactivity
│   ├── portfolio_callbacks.py      # Table/Metric updates
│   ├── positions_callbacks.py      # Ticker deep-dive logic
│   ├── watchlist_callbacks.py      # Watchlist logic
│   ├── signals_callbacks.py        # Manual signal generation
│   ├── intelligence_callbacks.py   # Modal & Drill-down logic
│   └── research_callbacks.py       # AI chat interaction
│
├── pages/                          # Multi-page routing
│   ├── portfolio.py                # Holdings (/)
│   ├── positions.py                # Positions (/positions)
│   ├── watchlist.py                # Watchlist (/watchlist)
│   ├── intelligence.py             # Insights (/intelligence)
│   ├── analytics.py                # Deep Dive (/analytics)
│   └── settings.py                 # Settings & Investor Profile (/settings)
│
└── assets/                         # Static assets (Modular CSS)
    ├── base-tokens.css             # Design Tokens (CSS Variables)
    ├── base-reset.css              # Global resets
    ├── ui-components.css           # Modular UI blocks (Stat cards, etc.)
    ├── view-pages.css              # Page-specific layout overrides
    └── vendor.css                  # High-specificity Radix/Dash overrides
```

---

## Import Paths Reference

### Core Logic (Engine)
```python
from core.engine.portfolio_engine import build_holdings, compute_holding_pnl
```

### Market Services
```python
from services.market.data_fetcher import fetch_live, get_etf_name
```

### Persistence
```python
from data.repository import PortfolioRepository
from data.watchlist_repository import WatchlistRepository

repo = PortfolioRepository()
history = repo.load_transactions()
wl_repo = WatchlistRepository()
watchlist = wl_repo.load_watchlist()
```
