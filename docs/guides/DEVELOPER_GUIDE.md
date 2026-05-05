# Developer Guide & Architecture Overview

This document outlines the architecture, layer model, and data flow of the Portfolio Dashboard.

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
│  research, prediction)│   │  portfolio_engine.py) │   │  data/csv_handler.py) │
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
    - **Research Service (AI)**: Contextual portfolio reasoning via Gemini 2.5 Flash Lite.
    - **Web Search Service**: Live financial news integration via DuckDuckGo.
    - **Memory Service**: Persistent state management with rolling 7-day logs and long-term summaries.
    - **Intelligence Service**: Risk analysis (Sharpe, Volatility) and rule-based allocation alerts.
    - **Prediction Service**: Forecasting using Facebook Prophet with continuity correction.
3.  **Engine (Logic)**: The "Mathematical Core". Pure Python logic for P&L computation, tranche aggregation, and performance metrics. It has **zero dependencies on Network, I/O, or Dash.**
4.  **Data (Persistence)**: The `PortfolioRepository` provides a clean abstraction for data operations, decoupling the CSV logic from the rest of the application.
5.  **Domain (Models)**: Typed definitions (Pydantic/TypedDict) that enforce data contracts across all layers.
6.  **Foundation (Core/Config)**: System-wide utilities (Validators, TTL Caching, Logging) and environment configuration.

---

## Data Consistency (OHLC & P&L)
To ensure visual and mathematical consistency across the dashboard, the system uses `auto_adjust=True` for all historical market data fetching.
- **Why**: Standardizing on adjusted prices prevents "dividend drops" from appearing as artificial price crashes in Candlestick charts and prevents false signals in Technical Indicators (RSI/MACD).
- **Impact**: All historical OHLC values (Open, High, Low, Close) are adjusted proportionally to reflect corporate actions and dividends.
- **Limitation**: While this is ideal for performance visualization, it may cause a mismatch if comparing adjusted historical prices to raw historical purchase prices for very old transactions in stocks that have split. (Rare for ASX ETFs).

---

## Data Lifecycle & Hydration

The dashboard uses a "Pre-seeded Store" pattern to ensure the first paint is instantaneous even before the first interval callback fires.

### 1. Startup Hydration (app.py)
When the server starts, it performs a blocking load to prepare the initial state:
1.  **Load**: `repo.load_transactions()` reads raw data via the `PortfolioRepository`.
2.  **Build**: `portfolio_engine.build_holdings()` aggregates transactions into `Holdings`.
3.  **Enrich**: `market_service.fetch_live()` pulls current prices using parallel workers.
4.  **Seed**: `dcc.Store(id="portfolio-store", data=INITIAL_DATA)` is rendered into the layout.

### 2. Reactivity Loop
Once running, the dashboard follows a **Single Refresh Owner** pattern:
- **`update_txn_store`**: The exclusive writer for transaction data. It handles additions and periodic disk syncs.
- **`update_portfolio_store`**: The exclusive caller of `fetch_live()`. It reacts to transaction changes or interval ticks.
- All charts and metrics across all pages are decorated with `@callback(Input("portfolio-store", "data"))`, causing them to re-render automatically.
- This ensures only one market fetch occurs per cycle, even with multiple disparate triggers.

---

## Global State Management

The application utilizes a sophisticated `dcc.Store` ecosystem to manage state across multiple pages without expensive re-fetches.

### 1. The Portfolio Store (`portfolio-store`)
- **Role**: The single source of truth for all holding data, histories, and metrics.
- **Hydration**: Pre-seeded at startup in `app.py` to ensure instantaneous first-paint.
- **Reactivity**: Updated every 60s (via `live-interval` defined in `config/settings.py`) or immediately upon transaction entry.

### 2. Preference & Session Stores
- **`theme-store`**: Local storage persistence for light/dark mode preference.
- **`period-store` / `pnl-mode-store`**: Session storage persistence for user selections (Timeframe, $ vs %), ensuring selections persist when navigating between pages.
- **`positions-selected-ticker`**: Tracks the active ticker for the deep-dive panel on the Positions page.

### 3. UI Context Stores
- **`nav-link-store`**: Dynamically updates the header badges (Market Status, Last Refreshed) by listening to URL path changes.
- **`compact-mode-store`**: Controls the density of the main portfolio table.

---

## Directory Structure

```
portfolio_dashboard/
├── app.py                          # Entry point (Seeds stores + defines refresh loop + Browser Mgmt)
│
├── config/                         # Configuration layer
│   ├── settings.py                 # Settings + env vars (Refresh rates, CSV paths)
│   ├── constants.py                # Colors, static names, themes
│   └── logging.py                  # Logging configuration
│
├── core/                           # Foundation layer
│   ├── engine/                     # Pure logic (Math, Aggregation)
│   │   └── portfolio_engine.py     # The "Brain" of the app
│   ├── cache.py                    # TTL cache for API responses
│   ├── validators.py               # Transaction schema validation
│   └── exceptions.py               # Custom error types
│
├── models/                         # Domain layer
│   └── transaction.py              # Holding & Transaction schemas
│
├── services/                       # Orchestration layer
│   ├── market/                     # Network calls (yfinance)
│   │   ├── data_fetcher.py         # Enrichment logic (Realized Dividends, Bulk Fetch)
│   │   └── market_status.py        # ASX timezone/status logic
│   ├── alert_service.py            # Price/Target monitoring
│   ├── intelligence_service.py     # Hierarchical risk/allocation logic
│   ├── prediction_service.py       # Prophet-based forecasting with disk-caching
│   ├── research_service.py         # Gemini-powered analysis & portfolio reasoning
│   └── research_memory.py          # Persistent chat logs & rolling AI summaries
│
├── data/                           # Persistence layer
│   ├── repository.py               # Data Repository abstraction
│   ├── csv_handler.py              # CSV I/O with backup management
│   └── portfolio_builder.py        # Legacy shim for engine imports
│   └── cache/                      # Persistent disk cache (e.g., predictions.json)
│
├── components/                     # UI components
│   ├── charts/                     # go.Figure factories (Pure UI functions)
│   │   ├── dividend.py             # Dividend bar charts
│   │   ├── intelligence.py         # Sunburst & Risk charts
│   │   └── ...
│   ├── header.py                   # Shared navigation header
│   └── portfolio_layout.py         # Main HTML structure
│
├── callbacks/                      # Dash interactivity
│   ├── chart_callbacks.py          # Dashboard graph updates
│   ├── portfolio_callbacks.py      # Table/Metric updates
│   ├── intelligence_callbacks.py   # Modal & Drill-down logic
│   └── research_callbacks.py       # AI chat interaction & memory status
│
├── pages/                          # Multi-page routing
│   ├── portfolio.py                # Main Dashboard (/)
│   ├── analytics.py                # Secondary Metrics (/analytics)
│   ├── intelligence.py             # Risk Analysis (/intelligence)
│   ├── watchlist.py                # Future tracker (/watchlist)
│   ├── research.py                 # AI Assistant (/research)
│   └── etf_detail.py               # Ticker deep-dive (/etf/<ticker>)
│
└── assets/                         # Static assets (Modular CSS)
    ├── base.css                    # Resets & CSS Variables (Loads 1st)
    ├── vendor.css                  # Radix/Dash Overrides (Loads last)
    └── ...
```

## Technical Constraints (GEMINI.md Rules)

To maintain performance and reliability, the following rules are strictly enforced:

-   **No Network in Loops**: Never call `yf.Ticker` inside a loop. Use `yf.download()` for bulk fetches.
-   **Ticker Normalization**: Tickers in CSV are raw (e.g., `VAS`). The data layer appends `.AX` only for market fetches.
-   **Timezones**: Use `pytz` or `zoneinfo` for AEST checks. Never hardcode offsets.
-   **CSS Priority**: All styling must use CSS variables from `base.css`. Hardcoded hex colors in Python layouts are prohibited.
-   **ID Persistence**: Never change Dash component IDs; they are hardcoded in modular callbacks.

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
repo = PortfolioRepository()
history = repo.load_transactions()
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
- **Domain-Specific TTLs**: Separates heavy computations from the 60s live tick. Technical signals are cached for 24 hours (`TECHNICALS_CACHE_TTL`), and historical dividend processing is cached for 7 days (`DIVIDENDS_CACHE_TTL`).
- **Bulk Downloads**: Continues to use `yf.download()` for primary price history to minimize HTTP overhead.

## Styling & UI Architecture

### CSS Modularization & Loading

1.  **`base.css`**: Defines CSS variables and global resets. Must load first to ensure theme availability.
2.  **`components.css` / `forms.css` / `layout.css`**: Core UI logic.
3.  **`vendor.css`**: Contains heavy overrides. This loads last alphabetically, allowing us to override hardcoded component styles effectively.

### Overriding Dash 2.16+ (Radix UI)
Modern Dash components (like `dcc.Dropdown` and `dcc.DatePickerSingle`) use Radix UI primitives. These often render elements in "Portals" at the end of the document body, bypassing standard CSS nesting.

**Technical Strategy**:
- Use **Wildcard Attribute Selectors**: To catch dynamic or stubborn classes, we use selectors like `div[class*="dash-datepicker-content"]`.
- **High Specificity**: Many Radix components use inline styles. Aggressive use of `!important` within the `vendor.css` layer is sanctioned for these specific overrides to ensure theme consistency.

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
- **Sunburst Charts**: Hierarchical allocation (Sector/Geography) is rendered using `Plotly Sunburst` traces.
- **Drill-down**: Clicking a sector/region in the Sunburst triggers a modal displaying the exact ticker-level contribution.
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
- **Data Source**: Every time the dashboard refreshes (default 60s), the current state is appended to a local JSON snapshot (`data/cache/intraday_YYYY-MM-DD.json`).
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
