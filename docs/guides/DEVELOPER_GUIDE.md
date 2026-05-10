# Developer Guide & Architecture Overview

This document outlines the architecture, layer model, and data flow of the Folio Dashboard.

### Layer Model

The application follows a strictly decoupled layered architecture to ensure separation of concerns. A key distinction is the separation of **Market Services** (orchestration/network) from the **Engine** (pure math/logic).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION LAYER                              │
│  (app.py, pages/, callbacks/, components/, assets/)                         │
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
           └───────────────┬────────────┴───────────────┬───────────┘
                           ▼                            ▼
               ┌───────────────────────┐    ┌───────────────────────┐
               │      DOMAIN LAYER     │    │   FOUNDATION LAYER    │
               │ (models/transaction.py)    │   (core/, config/)    │
               └───────────────────────┘    └───────────────────────┘
```

### Layer Responsibilities

1.  **Presentation (UI/Assets)**: The entry point and orchestrator. It handles the "Shell" (HTML/CSS), multi-page routing, and interactive state (`dcc.Store`). It coordinates the flow by loading raw transactions from the **Data Layer** and passing them to the **Service Layer** for enrichment.
2.  **Service (Orchestration & Intelligence)**: Coordinates complex workflows and AI-driven insights. This layer handles external API calls (yfinance, Gemini), tiered caching, and logic-heavy services:
    - **Market Service**: Real-time pricing and metadata enrichment.
    - **Dividend Service**: Centralized logic for realized income, trend analysis, and projected distributions.
    - **Research Service (AI)**: Contextual portfolio reasoning via Gemini 2.5 Flash Lite.
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
- **`watchlist`**: Ticker membership and merged notes.
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

### 3. UI Context Stores
- **`nav-link-store`**: Dynamically updates the header badges (Market Status, Last Refreshed) by listening to URL path changes.
- **`compact-mode-store`**: Controls the density of the main portfolio table.
- **`research-usage-store`**: Persistent counter for Gemini API usage, reset daily.

---

## Related Documentation

For non-architectural details, please refer to:
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Setup instructions, environment configuration, and how to add new features.
- **[TESTING.md](../improvements/TESTING.md)**: Manual verification steps and automated test suite status.
- **[GEMINI.md](../../GEMINI.md)**: Coding rules, architecture constraints, and AI agent boundaries.

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
│   │   ├── pnl_history.py          # Today view (resampled)
│   │   ├── price_history.py        # Candlestick/Line charts
│   │   └── ...
│   ├── header.py                   # Shared navigation header
│   └── ui_helpers.py               # Stat cards & section wrappers
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
│   ├── portfolio.py                # Main Dashboard (/)
│   ├── positions.py                # Ticker deep-dive (/positions)
│   ├── watchlist.py                # Watchlist (/watchlist)
│   ├── intelligence.py             # Risk Analysis (/intelligence)
│   ├── analytics.py                # Allocation Treemaps (/analytics)
│   └── ai_analyst.py               # AI Research & Reports (/ai-analyst)
│
└── assets/                         # Static assets (Modular CSS)
    ├── base-tokens.css             # Design Tokens (CSS Variables)
    ├── base-reset.css              # Global resets
    ├── ui-components.css           # Modular UI blocks (Stat cards, etc.)
    ├── view-pages.css              # Page-specific layout overrides
    └── vendor.css                  # High-specificity Radix/Dash overrides
```

## Technical Constraints (GEMINI.md)

All technical development, math weights, and AI logic boundaries are governed by the **[GEMINI.md](../../GEMINI.md)** file. 

**Key Enforcements:**
-   **No Network in Loops**: Bulk `yf.download()` only.
-   **Relational Persistence**: Mandatory SQLite usage for all core state.
-   **Modular CSS**: Strict use of design tokens over hardcoded hex.
-   **Signal Integrity**: Strategy Engine is the source of truth, AI is for explanation only.

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

---

## Core Algorithms & Special Logic

### 1. Realized Dividend Engine
Unlike standard dashboards that only show current yield, this app computes **Realized Dividends** by correlating distribution history with purchase tranches.
- **Tranche Matching**: A dividend is only credited if `purchase_date < ex_dividend_date`.
- **Accuracy**: This prevents "phantom income" from showing up for stocks bought after their ex-date.

### 2. Prophet Forecasting & Continuity Correction
The forecasting engine in `prediction_service.py` uses Facebook Prophet with a custom "Continuity Correction" layer.
- **The Problem**: Trends fitted by Prophet often have a vertical gap between the last historical price and the first forecasted point.
- **The Fix**: We calculate the `drift` (Actual Last - Fitted Last) and apply it as a vertical offset to the entire forecast series, ensuring a smooth visual transition.

### 3. Advanced Risk Metrics
Metrics in `intelligence_service.py` are calculated using standard financial formulas:
- **Sharpe Ratio**: `(Mean Excess Return / Std Dev of Return) * sqrt(252)`, using a 4.35% (Current RBA/Fed-proxy) risk-free rate.
- **Volatility**: Annualized standard deviation of daily log returns.
- **Drawdown**: Percentage drop from the previous all-time high in the selected period.

### 4. Parallel Market Fetching & Caching
To ensure high performance with multi-ticker portfolios, the `fetch_live` service utilizes concurrency:
- **Parallel Workers**: Uses `ThreadPoolExecutor` (10 workers) to parallelize sequential I/O-bound requests (e.g., `ticker.info` for names and dividends).
- **Metadata Caching**: Implements a simple in-memory TTL cache for Yahoo Finance metadata, avoiding redundant network calls for static data (ETF names, payout frequencies).
- **Domain-Specific TTLs**: Separates heavy computations from the 300s live tick. Technical signals are cached for 24 hours (`TECHNICALS_CACHE_TTL`), and historical dividend processing is cached for 7 days (`DIVIDENDS_CACHE_TTL`).
- **Bulk Downloads**: Continues to use `yf.download()` for primary price history to minimize HTTP overhead.

## Styling & UI Architecture

### CSS Token System

The application uses a strictly themed design system defined in `assets/base-tokens.css`. Developers must use these variables instead of hardcoded hex values to ensure theme consistency.

| Category | Tokens | Purpose |
|----------|--------|---------|
| **Theme** | `--bg`, `--surface`, `--surface-2` | Base layers & card backgrounds |
| **Type** | `--t-pri`, `--t-sec`, `--t-muted` | Hierarchical typography colors |
| **Brand** | `--cyan`, `--cyan-2` | Primary accents & active states |
| **Status** | `--green`, `--red`, `--warning` | Semantic feedback (P&L, Alerts) |
| **Lines** | `--border`, `--border-2` | Section dividers & accent borders |

### CSS Modularization & Loading

1.  **`base-tokens.css`**: Defines CSS variables.
2.  **`base-reset.css`**: Global resets and base typography.
3.  **`ui-components.css`**: Shared component blocks.
4.  **`vendor.css`**: High-specificity overrides for Radix/Dash components.

### Overriding Dash 2.16+ (Radix UI)
Modern Dash components often render elements in "Portals" at the end of the document body. 
- Use **Wildcard Attribute Selectors** (e.g., `div[class*="dash-datepicker"]`).
- Aggressive use of `!important` within the `vendor.css` layer is sanctioned for these overrides to ensure theme consistency across portal boundaries.

### Transaction Flow Migration
The transaction entry system was migrated from a standard `dcc.Input` to a Mantine `dmc.DateInput` for a more polished UI.

- **Component**: `dmc.DateInput` in `components/portfolio_layout.py`.
- **State Change**: In `callbacks/transaction_callbacks.py`, the callback now listens to the `value` property (ISO YYYY-MM-DD string).
- **Validation**: The `validate_transaction` service remains compatible as it expects the same ISO format.

---

## Specialized Features

### 1. Intelligence & Risk Analysis
The **Intelligence Page** provides a deep dive into portfolio risk.
- **Metrics**: Annualized Volatility, Sharpe Ratio, and Max Drawdown are calculated using pure Python in `intelligence_service.py`. 
- **Optimization**: To avoid double-calculating heavy return series (e.g. when forecasting is enabled), returns are pre-computed once and passed into the metrics engine.
- **Robustness**: Safety checks ensure that missing ETF metadata (`funds_data`) doesn't crash the engine; it falls back to parsing the `info` category or symbol-based inference.
- **Treemap Charts**: Hierarchical allocation (Sector/Geography) is rendered using `Plotly Treemap` traces for high-density space efficiency.
- **Drill-down**: Clicking a sector/region in the Treemap triggers a modal displaying the exact ticker-level contribution.
- **Smart Alerts**: A rule-based engine evaluates the portfolio against `THRESHOLDS` (e.g., >40% in one sector) to generate actionable insights.

### 2. Portfolio Forecasting (Prophet)
Forward-looking projections are handled by `prediction_service.py`.
- **Model**: Uses Facebook Prophet with Australian holiday awareness.
- **Tiered Caching**: To ensure UI responsiveness, forecasts are computed once and stored in `data/cache/predictions.json` (disk cache) and also held in the `dcc.Store` (client cache).
- **Confidence Intervals**: Displays an 80% uncertainty band to highlight potential market volatility.

### 3. Realized Dividend Tracking
Unlike standard yield calculations, the app computes **Realized Dividends** by matching historical Ex-Dividend dates against the user's specific holding tranches. 
- **Logic**: A dividend is "realized" only if the tranche purchase date is strictly before the Ex-Dividend date.
- **Accuracy**: This provides a dollar-accurate representation of income actually earned, rather than a theoretical annual yield based on current price.

### 4. Intraday Market Sessions (Today View)
The "Today" P&L view utilizes a dedicated intraday tracking system to provide real-time updates without the limitations of standard daily-interval data.
- **Data Source**: Every time the dashboard refreshes (default 300s), the current state is appended to a local JSON snapshot (`data/cache/intraday_YYYY-MM-DD.json`).
- **Bypass Strategy**: The P&L History chart reads this file directly when in "1d" mode. This bypasses the main `portfolio-store` for chart rendering, preventing "Timezone Concat" errors that occur when mixing historical daily data (often UTC-naive) with live intraday data (Sydney wall-clock).
- **Window**: The chart is strictly pinned to the ASX trading window (10:00 AM – 4:15 PM Sydney Time).
- **Persistence**: Snapshotting ensures that intraday progress is preserved even if the application is restarted during the trading day.
### 5. Technical Indicators Engine (Pure Pandas)
The **Technical Indicators Service** (`services/technical_indicators.py`) provides high-performance technical analysis without external TA library dependencies.
- **Pure Pandas Math**: All indicators (RSI, MACD, Bollinger Bands) are implemented using native pandas vectorized operations (`ewm`, `rolling`, `std`) to ensure portability and speed.
- **Wilder's Smoothing**: The RSI implementation uses Wilder's method (`com=period-1`) to match industry-standard trading platforms.
- **Standardized Signals**: The `compute_signals` function returns a consistent 10-key dictionary, including human-readable labels (e.g., "Oversold", "Bullish") for immediate UI consumption.

### 6. OHLC Data Architecture & Candlestick Support
The data fetching layer was enriched to support high-fidelity price visualization.
- **OHLC Extraction**: The `data_fetcher.py` now extracts `Open`, `High`, and `Low` columns in addition to `Close`. 
- **Graceful Fallback**: Since the "1d" (intraday) period often lacks OHLC columns, the system implements a fallback to standard Line charts (`go.Scatter`) when Candlestick data is unavailable.
- **Data Cleansing**: The fetcher performs a strict `dropna(subset=["Close"])` and timezone normalization on combined OHLC frames to prevent rendering crashes.

### 7. Multi-Page Period Synchronization
To ensure consistent data views across the dashboard, the application implements a "Global Max Period" strategy.
- **The Problem**: Different pages (e.g., Positions vs. Watchlist) may request different time periods, but they share the global `portfolio-store`.
- **The Fix**: The refresh callback in `app.py` evaluates all active page-specific period stores and instructs the market service to fetch the **maximum** duration requested. This ensures that when a user switches pages, the required historical data is already present in the global cache.

### 8. AI Research Assistant & Persistent Memory
The **Research Page** leverages Google Gemini 2.5 Flash Lite for contextual portfolio reasoning.
- **Contextual Awareness**: On every query, the assistant is injected with a live snapshot of the portfolio (Holdings, P&L, Weights) and the ticker currently being researched.
- **Technical Integration**: Live technical signals (RSI/MACD/BB) are automatically computed and injected into the prompt context, allowing the AI to reason about technical entry points.
- **Cost & Performance Optimization**:
    - **Deterministic Caching**: To minimize Gemini API costs, the `ai_engine.py` generates a cache key based on a stable subset of signals (Signal + Rounded Score). Highly volatile live price ticks are ignored for cache key generation, preventing redundant paid API calls.
    - **SDK Compatibility**: The engine uses the `google.genai` SDK with standardized parameter sets to ensure reliability and 10s-range response times.
- **Rolling Memory Pattern**: To provide continuity without bloating storage, the system uses a dual-layer memory:
    - **Short-Term (7-day Log)**: Exact conversation turns stored in `conversation_log.json`.
    - **Long-Term (AI Summary)**: On startup, old turns are automatically summarized into bullet points by Gemini and saved to `memory_summary.json`.
- **Usage Monitoring**: A daily message limit (20) and storage cap (50MB) are enforced to ensure system stability.
- **Startup Maintenance**: The `run_startup_maintenance` routine in `app.py` ensures the memory remains pruned and summarized before the app accepts user input.

### 9. Live Web Search Integration
The research assistant is now equipped with real-time web search capabilities to supplement portfolio context.
- **Trigger**: The `should_search_web` function evaluates user messages for financial keywords (e.g., "announcement", "forecast", "asx").
- **Smart Querying**: If a search is triggered, the system constructs a targeted query combining the user message with the active ticker context.
- **Provider**: Powered by `duckduckgo-search` (via the `ddgs` package), fetching the most recent (last month) Australian financial news.
- **UI Feedback**: Assistant responses that incorporate web data are clearly marked with a `🔍 Web search used` indicator.

### 10. Technical Charting & UI Layout Stability
To provide a professional trading experience, the dashboard implements several layout and visualization safeguards:
- **Layout Isolation (AI Insights)**: To prevent large blocks of AI-generated text from disrupting the CSS Grid, AI Analyst insights are rendered in a dedicated `ai-insight-container`. This prevents the "auto-fit" behavior from shrinking the top-level metric cards when the AI card expands.
- **Dynamic Chart Scaling**: Price charts on the Watchlist page calculate the period's min/max prices dynamically. The Y-axis is constrained to `[min * 0.98, max * 1.02]`, eliminating the massive empty gap at the bottom of the chart caused by the default "start at $0" behavior (common in `fill="tozeroy"` charts).
- **Typography Standards**: All AI-generated explanations use standard 13px body font sizes with 1.5 line height for readability, while technical metrics (e.g., RSI Score) are consistently themed using the primary accent color (`var(--cyan)`).

### 11. UI Layout Standardization (Grid & Sectioning)
To eliminate visual inconsistencies and "compactness" issues, the dashboard follows a strict 24px horizontal grid.
- **Header Standard**: `.page-header-row` is fixed at `padding: 16px 24px`.
- **Structural Wrappers**: All major content blocks must be wrapped in the `section()` helper from `components.ui_helpers`. This enforces a `0.5px` bottom border and a uniform `16px 24px` padding.
- **Dynamic Rendering**: To prevent "empty dashboard syndrome", pages use dynamic containers (e.g., `positions-price-chart-container`) that hide headers and empty plots until a ticker is selected, ensuring the initial state is clean and professional.

### 12. Deterministic Strategy Engine & AI Critique
The dashboard includes a hybrid decision-support system:
- **Strategy Engine** (`services/strategy_engine.py`): Pure, rule-based logic that generates BUY/SELL/HOLD signals based on five weighted dimensions (Trend, Momentum, Price vs 200MA, Price vs Cost, and Risk).
- **AI Analyst Overlay** (`services/ai_engine.py`): Gemini critiques the deterministic signals, providing human-readable context and risk flags without overriding the engine's verdict.
- **Hysteresis**: To prevent signal flickering on volatile days, the engine implements a "flip-prevention" logic where a signal change is only accepted if the new score exceeds a 0.7 confidence threshold.
- **Overview Integration**: Signals from the engine are automatically injected into the main Portfolio Overview table as a "Suggestion" badge, allowing users to see actionable insights alongside live performance data.

### 13. Intraday Resampling & Resiliency
To ensure the "Today" P&L chart remains professional and readable:
- **5-Minute Resampling**: Live data is resampled to 5-minute intervals (`resample('5min').last().ffill()`) to eliminate jagged visual artifacts.
- **Trading Session Stitching**: Plotly `rangebreaks` are applied to the X-axis to hide overnight sessions and weekends, creating a continuous trading timeline.
- **Background Snapshotting**: A dedicated thread in `app.py` records market snapshots every 5 minutes while the market is open, ensuring chart continuity even if the dashboard is closed.

### 14. Analytics Visualization & Theme Integration
To provide a seamless visual experience, the Allocation and Performance charts in the Analytics page are deeply integrated with the design system.
- **Background Harmonization**: All Plotly figures utilize `paper_bgcolor="rgba(0,0,0,0)"` and `plot_bgcolor="rgba(0,0,0,0)"`, ensuring they blend perfectly with the CSS `var(--surface)` layer without grey "canvas" artifacts.
- **Theme-Aware Typography**: Labels and titles are dynamically mapped to CSS variables (e.g., `var(--t-pri)`), ensuring high contrast and readability across both light and dark modes.
- **Template Stripping**: Standard Plotly templates are disabled to prevent legacy styling (like default grid lines or grey backgrounds) from leaking into the modern dashboard aesthetic.

### 15. Standardized Architecture Compliance
Following a project-wide audit, the application adheres to strict operational standards:
- **Logging Purity**: All `print()` statements in the service and data layers have been replaced with `logger.debug()` or `logger.info()` to ensure a clean production console and detailed file-based troubleshooting.
- **Callback Safety**: The `prevent_initial_call=True` flag is mandatory for all page-specific callbacks to prevent race conditions and "empty data" rendering glitches during multi-page navigation.


### 16. Callback Prioritization & Rendering Efficiency
To maintain 60FPS UI responsiveness even when global stores update frequently, the dashboard implements **URL-Aware Prioritization**:
- **Guard Clause**: Every page-specific rendering callback includes `Input("url", "pathname")`.
- **Logic**: If the current `pathname` does not match the callback's page, it returns `dash.no_update` immediately.
- **Benefit**: This eliminates "DOM thrashing" where off-screen charts attempt to re-render in the background, significantly reducing CPU spikes during market hours.

### 17. Standardized Chart Fallbacks
To prevent the appearance of broken "empty grid" charts during data loading or error states:
- **Centralized Helper**: All charts must use `create_empty_fig()` from `components.charts.helpers`.
- **Visual Consistency**: This ensures that even without data, the dashboard remains professional and provides user-friendly "Waiting for data..." annotations.

### 18. UI Aesthetics & Live Tracking
To create a premium, "live" feel similar to modern fintech applications, the dashboard implements smooth value transitions:
- **CSS Transitions**: Major numeric values (Portfolio P&L, Card Metrics, Summary Strips) utilize `transition: all 0.3s ease`.
- **UX Impact**: When the 300s background refresh fires, numbers smoothly ease into their new values rather than snapping instantly, making the app feel alive and responsive.

### 19. Loading Experience (Skeletons & uirevision)
To ensure a professional "Day 1" experience and prevent UI flicker during updates:
- **Fixed-Column Skeletons**: To prevent layout shift (vertical stacking) during loading, `custom_spinner` containers utilize fixed-column grids (e.g., `repeat(6, 1fr)`) with explicit `width: 100%`. This ensures skeletons occupy the exact same space as the final data.
- **Stable Charts (uirevision)**: All major Plotly figures implement `uirevision=True` (or a context-stable string like `ticker`). This ensures that background data updates do NOT reset the user's zoom or pan position, allowing for seamless background refreshes.
- **Skeleton Helpers**: Standard placeholders are available in `components/ui_helpers.py` (`stat_card_skeleton`, `chart_skeleton`, `table_skeleton`) and should be used as the `custom_spinner` for all `dcc.Loading` wrappers.
