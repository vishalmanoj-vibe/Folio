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
│ (market, intelligence,│   │ (core/engine/         │   │ (data/csv_handler.py) │
│  alert, prediction)   │   │  portfolio_engine.py) │   │                       │
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
2.  **Service (Orchestration)**: Coordinates complex workflows including external API calls (yfinance), tiered caching, and domain-specific logic like alert detection, hierarchical risk analysis, and Prophet forecasting.
3.  **Engine (Logic)**: The "Mathematical Core". Pure Python logic for P&L computation, tranche aggregation, and performance metrics. It has **zero dependencies on Network, I/O, or Dash.**
4.  **Data (Persistence)**: Handles direct I/O operations (CSV) and transactional integrity for the portfolio history.
5.  **Domain (Models)**: Typed definitions (Pydantic/TypedDict) that enforce data contracts across all layers.
6.  **Foundation (Core/Config)**: System-wide utilities (Validators, TTL Caching, Logging) and environment configuration.

---

## Data Lifecycle & Hydration

The dashboard uses a "Pre-seeded Store" pattern to ensure the first paint is instantaneous even before the first interval callback fires.

### 1. Startup Hydration (app.py)
When the server starts, it performs a blocking load to prepare the initial state:
1.  **Load**: `csv_handler.load_csv()` reads raw transactions.
2.  **Build**: `portfolio_engine.build_holdings()` aggregates transactions into `Holdings`.
3.  **Enrich**: `market_service.fetch_live()` pulls current prices and computes P&L.
4.  **Seed**: `dcc.Store(id="portfolio-store", data=INITIAL_DATA)` is rendered into the layout.

### 2. Reactivity Loop
Once running, the `dcc.Interval` (default 60s) triggers the `refresh_portfolio_data` callback:
- It repeats the **Load -> Build -> Enrich** cycle.
- The updated JSON is pushed to `portfolio-store`.
- All charts and metrics across all pages are decorated with `@callback(Input("portfolio-store", "data"))`, causing them to re-render automatically.

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
│   └── prediction_service.py       # Prophet-based forecasting with disk-caching
│
├── data/                           # Persistence layer
│   ├── csv_handler.py              # CSV I/O with backup management
│   ├── portfolio_builder.py        # Legacy shim for engine imports
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
│   └── intelligence_callbacks.py   # Modal & Drill-down logic
│
├── pages/                          # Multi-page routing
│   ├── portfolio.py                # Main Dashboard (/)
│   ├── analytics.py                # Secondary Metrics (/analytics)
│   ├── intelligence.py             # Risk Analysis (/intelligence)
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
from data.csv_handler import load_csv, save_csv
```
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
