# Developer Guide & Architecture Overview

This document outlines the architecture, layer model, and data flow of the Portfolio Dashboard.

### Layer Model

The application follows a strictly decoupled layered architecture to ensure separation of concerns. A key distinction is the separation of **Market Services** (orchestration/network) from the **Engine** (pure math/logic).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION LAYER                              │
│  ┌────────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │     STATIC ASSETS      │  │    DASH COMPONENTS   │  │  DASH CALLBACKS  │  │
│  │ (assets/*.css modules) │  │ (pages/, components/) │  │   (callbacks/)   │  │
│  └───────────┬────────────┘  └───────────┬──────────┘  └─────────┬────────┘  │
└──────────────┼───────────────────────────┼───────────────────────┼──────────┘
               │                           ▼                       │
               │               ┌───────────────────────┐           │
               └──────────────►│    SERVICE LAYER      │◄──────────┘
                               │ (services/market,     │
                               │  intelligence, alert) │
                               └───────────┬───────────┘           
                                           ▼                       
                               ┌───────────────────────┐           
                               │     ENGINE LAYER      │           
                               │ (core/engine/portfolio)│
                               └───────────┬───────────┘           
                                           ▼                       
                               ┌───────────────────────┐           
                               │    DATA ACCESS LAYER  │           
                               │ (data/, csv_handler.py)           
                               └───────────┬───────────┘           
                                           ▼                       
                               ┌───────────────────────┐           
                               │      DOMAIN LAYER     │           
                               │ (models/, transaction.py)         
                               └───────────┬───────────┘           
                                           ▼                       
                               ┌───────────────────────┐           
                               │   FOUNDATION LAYER    │           
                               │    (core/, config/)   │           
                               └───────────────────────┘           
```

### Layer Responsibilities

1.  **Presentation (UI/Assets)**: Handles the "Shell" (HTML/CSS) and the interactive state. Uses `dcc.Store` for client-side state management. CSS is modularized to ensure theme consistency.
2.  **Service (Orchestration)**: Coordinates external API calls (yfinance), caching, and complex business workflows like alert detection or hierarchical risk analysis.
3.  **Engine (Logic)**: Pure Python logic for P&L computation, tranche aggregation, and performance metrics. **Zero dependencies on Dash or Network.**
4.  **Data (Persistence)**: Handles I/O operations (CSV) and transactional integrity.
5.  **Domain (Models)**: Typed definitions (Pydantic/TypedDict) that enforce data contracts across layers.
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
├── app.py                          # Entry point (Seeds stores + defines refresh loop)
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
│   │   ├── data_fetcher.py         # Enrichment logic
│   │   └── market_status.py        # ASX timezone/status logic
│   ├── alert_service.py            # Price/Target monitoring
│   └── intelligence_service.py     # Hierarchical risk/allocation logic
│
├── data/                           # Persistence layer
│   ├── csv_handler.py              # CSV I/O with backup management
│   └── portfolio_builder.py        # Legacy shim for engine imports
│
├── components/                     # UI components
│   ├── charts/                     # go.Figure factories (Pure UI functions)
│   └── portfolio_layout.py         # Main HTML structure
│
├── callbacks/                      # Dash interactivity
│   ├── chart_callbacks.py          # Dashboard graph updates
│   ├── portfolio_callbacks.py      # Table/Metric updates
│   └── intelligence_callbacks.py   # Modal & Drill-down logic
│
├── pages/                          # Multi-page routing
│   ├── portfolio.py                # Main Dashboard
│   ├── intelligence.py             # Risk Analysis
│   └── etf_detail.py               # Ticker deep-dive
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
The transaction entry system was migrated from a standard `dcc.Input` to a `dcc.DatePickerSingle`.

- **Component**: `dcc.DatePickerSingle` in `components/portfolio_layout.py`.
- **State Change**: In `callbacks/transaction_callbacks.py`, the callback now listens to the `date` property (ISO YYYY-MM-DD string) instead of the `value` property.
- **Validation**: The `validate_transaction` service remains compatible as it expects the same ISO format.
