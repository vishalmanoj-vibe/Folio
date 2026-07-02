# Project Evolution & Build History — Performance Era

> Back to [BUILD_HISTORY.md](BUILD_HISTORY.md)

This document details the performance optimization, data reliability, and dual-process scaling phases of Folio, leading up to version v2.0.0.

> [!NOTE]
> **Versioning Typographical Correction:**
> The versions `v3.6.0 – v3.9.0` documented in early phases were typographical errors in the original logs. Chronologically and relative to git tags, these actually correspond to releases `v1.36.0 – v1.39.0` preceding the major `v2.0.0` architecture overhaul.

---

## Phase 7: Rendering Prioritization & UX Polish (v1.36.0 – v1.37.0)
*(Note: Documented as v3.6.0 – v3.7.0 in legacy logs)*

**Theme**: Optimizing for extreme responsiveness, visual stability, and aesthetic excellence.

*   **Fast Startup Architecture**: Refactored the core application lifecycle to eliminate blocking market data fetches during initialization. The dashboard now boots instantly (<1s) using disk-cached state, with live data refreshing in the background after the UI is interactive.
*   **Rendering Prioritization**: Implemented a URL-aware callback strategy that eliminates "DOM thrashing" and UI flicker. By making rendering callbacks aware of the active page, the browser only updates visible components, significantly reducing CPU load during high-frequency market updates.
*   **UI Stabilization & Skeletons**: Integrated brand-aligned, pulsing skeleton loaders across all data-bound containers. Developed **fixed-column grid skeletons** to eliminate "layout shift" where the UI would jump or stack vertically before data arrived.
*   **Persistent Chart State (uirevision)**: Implemented stable `uirevision` keys across all major visualizations. This ensures that 5-minute background data refreshes do NOT reset user zoom, pan, or toggles, creating a seamless "tracking" experience.
*   **Live Tracking Aesthetics**: Applied 300ms CSS transitions to all key financial metrics. Data updates now smoothly ease into place, mimicking the fluid feel of high-end fintech dashboards.
*   **Standardized Empty States**: Introduced a centralized chart fallback system (`create_empty_fig`) to ensure all visualizations maintain a professional aesthetic during loading or error states.

---

## Phase 8: Aesthetic Excellence & Chart Standardization (v1.38.0 – Current)
*(Note: Documented as v3.8.0 – Current in legacy logs)*

**Theme**: Standardizing the visual language and achieving "Linear-grade" UI polish.

*   **Unified Chart Architecture**: Refactored the entire charting library to use a centralized `apply_standard_layout` helper. This enforced a single source of truth for **Inter 10px** typography, unified hover models, and grid opacities across all 15+ dashboard visualizations.
*   **Glassmorphism Navigation**: Implemented a frosted-glass navigation bar with `backdrop-filter: blur(12px)` and semi-transparent layers, optimized for high-performance rendering in WebKit (Safari).
*   **Theme Transition Smoothness**: Eliminated jarring visual snaps by implementing **200ms CSS transitions** on all theme-aware properties (background-color, color, border-color) across the entire application shell.
*   **Data Freshness Pulse**: Introduced a live "heartbeat" indicator in the header. The animated status dot pulses green during market hours and remains static grey otherwise, providing at-a-glance evidence of live monitoring.
*   **Interactive Depth & Typography**: Standardized on **Inter with tabular numerals** for financial accuracy and added interactive hover states (lift + teal glow) to all dashboard cards.

---

## Phase 9: Performance Baseline & Multi-Tier Intervals (v1.39.0 – Current)
*(Note: Documented as v3.9.0 – Current in legacy logs)*

**Theme**: Profiling the dashboard and optimizing network overhead.

*   **Performance Baselines**: Integrated `memory_profiler` and `psutil` to establish and document memory and CPU baselines for all core rendering and fetch callbacks.
*   **Multi-Tier Interval Strategy**: Replaced the unconditional 5-minute global refresh with a multi-tier interval strategy:
    *   **UI Heartbeat (30s)**: A fast `live-interval` updates badges, statuses, and time-ago counters without network impact.
    *   **Data Refresh (300s)**: A new `price-interval` exclusively orchestrates data fetches.
    *   **Market Hours Gating**: The periodic `price-interval` is strictly gated to market hours, while manual refreshes, initialization, and transaction events continue to bypass the gate, ensuring 100% responsiveness during off-hours with zero redundant Yahoo Finance network calls.
*   **Intelligent Background Snapshotting**: Upgraded the `background_refresh` daemon thread from naive polling to dynamic sleep durations. The thread now accurately calculates the time until the next market open (accounting for Daylight Savings and ASX Public Holidays) and sleeps deeply during off-hours, significantly reducing system resource usage.
*   **Lazy Loading Prophet**: Implemented a lazy loading architecture for Facebook Prophet in the `prediction_service`. The heavy forecasting dependencies are now only loaded into memory when explicitly requested by the user, drastically reducing startup overhead and baseline memory consumption.
*   **Bounded Memory Caching**: Refactored the core caching system (`core/cache.py`) to enforce a strict memory ceiling. Introduced dynamic eviction passes (`MAX_CACHE_ENTRIES`) to forcefully reap stale metrics and orphaned data segments, preventing unbounded memory creep during long-running sessions.
*   **Automated Phase 1 Verification**: Built a deterministic testing pipeline (`scripts/verify_phase1.py`) using isolated AST parsing and dependency monkey-patching to systematically verify market gating, Prophet lazy-loading, cache evictions, and dynamic background sleep cycles without mutating source code.
*   **Server-Side History Persistence**: Decommissioned browser-side historical price arrays. All historical data (OHLC, Dividends) has been moved to a server-side **SQLite backed repository (`price_history`)**, reducing the primary `portfolio-store` JSON payload from ~1.6MB to under 20KB and eliminating UI lag during serialization.
*   **Lazy Ticker Fetching**: Transitioned from global portfolio-wide history fetching to a **per-page lazy-loading strategy**. The detail pages (Positions, Watchlist) now fetch their own history on-demand via a standalone `fetch_ticker_history()` service, reducing redundant network data transfer and processing by ~80% on the main dashboard refresh.
*   **Memory Footprint Reduction (Compact DFs)**: Implemented a compact caching strategy for yfinance downloads. Instead of storing multi-megabyte `multi_full` DataFrames, the system now extracts and caches individual, compact `pd.Series` for Close prices and Dividends. Raw bulk DataFrames are discarded immediately, preventing unbounded RAM creep and achieving a **55% reduction in baseline RSS memory usage**.
*   **Relational History Management**: Established a robust `HistoryRepository` with market-aware staleness checks (5m cooldown during trading / 24h otherwise) and automated record cleanup, ensuring the `portfolio.db` remains performant and sized optimally.

---

## Phase 10: Enterprise-Grade Memory Hygiene & Distributed Architecture (v2.0.0 – Current)
**Theme**: Scaling the architecture for long-running sessions and complex scrapers.

*   **Dual-Process Resilience**: Implemented a `launcher.py` process manager that separates the Dash UI from the data-heavy background worker, ensuring the UI remains responsive even during heavy Technical Analysis or AI signal generation.
*   **Startup Task Decentralization**: Offloaded intensive historical data hydration (e.g., Watchlist histories) from the web startup sequence to the background worker. This achieved a 40% reduction in web-process startup memory.
*   **Distributed Scraper Offloading**: Moved the *execution* of the ETF holdings scraper (including Playwright/WebKit sessions) to the background worker. The Dash UI now enqueues these as asynchronous tasks, preventing massive 1GB+ RAM spikes in the web process.
*   **Smart Depth Awareness**: Refactored the `is_stale` logic to handle young tickers (listed < 220 days). By tracking the history 'period' in metadata, the system now avoids redundant daily "max" history fetches for stocks that have already provided their full available history.
*   **Metadata Truncation**: Implemented aggressive truncation for yfinance `info` objects. Only essential metadata (name, sector, yield) is persisted to SQLite, preventing "Heap Bloat" from unused nested dictionaries.
*   **Historical Staleness Gating**: Enforced a strict 24-hour staleness threshold for historical data, while maintaining 5-minute resolution for intraday P&L tracking.
*   **UI Hover Stability**: Standardized Plotly `hovertemplate` syntax to use doubled-braces (`%{{y}}`), eliminating `NameError` crashes during normalized chart rendering.
*   **Watchlist Drag-and-Drop Reordering**: Introduced manual, interactive grab-handle (`☰`) reordering for watchlist tickers. Added a custom, Event-Delegated HTML5 drag-and-drop client script (`assets/drag_drop.js`) that persists across Dash DOM refreshes and gates starts on drag handles via mousedown target tracking. Synchronizes the new order with a SQLite `order_index` column via a hidden `#watchlist-order-input` dcc.Input state bridge under a clean transactional block.
*   **Underlying ETF Holdings Integration**: Integrated underlying ETF holdings data directly into the Allocation Treemap under the new "Underlying Holdings" filter option. Removed the separate ETF Holdings tab and its bubble chart to simplify page navigation. Implemented space-efficient flat underlying company nodes sized by absolute dollar values, styled using the standard Allocation colorscale, and enriched with hover tooltips listing source ETF contribution breakdowns. Handled empty cache states gracefully by rendering clear warnings and auto-opening the Configure Sources panel.
*   **Ticker Normalization and Name Resolution**: Implemented case-insensitive ticker suffix normalization (`.AX` / `.ax` removal) across all transaction submission and discovery callbacks, resolving `.AX.AX` double-suffix corruption. Enforced central display name merging from the `assets` metadata table into `get_live_prices` queries via a SQL `LEFT JOIN`, ensuring long names dynamically resolve for newly added tickers. Standardized `prev_close`, `day_high`, and `day_low` columns in `market_prices` schemas and migration scripts to prevent columns from being overwritten to `NULL`.
*   **ETF Underlying Holdings Restructuring & URL Config Sync**: Restructured the "Underlying Holdings" treemap to use a nested Ticker -> Company hierarchy. Grouped stocks under their parent ETF tickers as child nodes (uniquely identified as `f"{ticker}_{company}"` to prevent duplicate ID collisions), and consolidated multiple flat "Other" nodes into a per-ETF "Other" leaf. Satisfied Plotly's `branchvalues="total"` constraint by dynamically assigning residual weights to the final child node of each ETF. Upgraded the URL configuration table to automatically display all transaction portfolio tickers, registered `URNM` directly in `PROVIDER_SEED_URLS` with its official BetaShares page, and implemented an auto-persistence mechanism in `fetch_holdings` to save DDGS-discovered URLs to `etf_holdings_urls` in SQLite upon a successful scrape. Rendered unconfigured URLs safely as unclickable text spans instead of broken hyperlinks.
