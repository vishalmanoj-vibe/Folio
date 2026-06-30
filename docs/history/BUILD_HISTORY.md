# Project Evolution & Build History

This document chronicles the technical evolution of Folio, transitioning from a basic tracking tool into a sophisticated, AI-driven market intelligence platform.

---

## Phase 1: Foundations & UI (v0.1.0 – v0.4.0)
**Theme**: Establishment of core navigation and basic P&L tracking.

*   **Initial Prototype**: Established the multi-page Dash structure with a shared sidebar and persistent stores.
*   **Design System**: Implemented the first iteration of Light/Dark mode and a basic grid layout.
*   **Early Intelligence**: Added exposure calculations and category drill-downs to understand basic asset allocation.
*   **Infrastructure**: Added the first `Developer Guide` to standardize component-based development.

---

## Phase 2: Deep Dive & Market Insights (v0.5.0 – v1.0.0)
**Theme**: Moving beyond static data with forecasting and real-time intraday tracking.

*   **Predictive Analysis**: Integrated **Facebook Prophet** for forward-looking price projections with confidence intervals.
*   **Dividend Engine**: Developed a custom "Realized Dividend" logic that matches tranche purchase dates against historical ex-dividend dates for dollar-accurate income tracking.
*   **Intraday Snapshots**: Solved the "Jagged Data" problem by implementing a local JSON snapshotting system for 5-minute intraday tracking within ASX session windows.
*   **Visualization Overhaul**: Replaced standard charts with high-density **Treemaps** for allocation and **Lollipop** charts for performance metrics.

---

## Phase 3: Performance & Scalability (v1.1.0 – v1.5.0)
**Theme**: Architectural optimization to handle growing portfolios and high-frequency data.

*   **Parallel Fetching**: Implemented `ThreadPoolExecutor` and bulk `yf.download()` requests to reduce market data loading times by ~70%.
*   **CSS Modularization**: Transitioned from a monolithic `base.css` to a component-based directory (`tokens`, `layout`, `components`), significantly reducing style collisions.
*   **State Management**: Optimized `dcc.Store` usage, separating the heavy `portfolio-store` (data) from session-scoped UI preferences.
*   **Metadata Caching**: Added persistent caching for ETF metadata to avoid redundant Yahoo Finance API calls.

---

## Phase 4: The Assistant & Technical Engine (v1.6.0 – v2.2.0)
**Theme**: Integrating Generative AI and quantitative technical analysis.

*   **Research Assistant**: Integrated **Google Gemini (flash-lite)** with full portfolio context awareness for interactive research.
*   **Technical Engine**: Developed a pure-pandas technical analysis engine (no external libs) to compute **RSI**, **MACD**, and **Bollinger Bands** on the fly.
*   **AI Search Service**: Enabled real-time market intelligence by integrating a live web-search service into the AI's research context.
*   **Report Generation**: Built a backend PDF service to generate weekly automated summaries with P&L performance charts and news sentiment.

---

## Phase 5: Architectural Maturity & Relational Migration (v2.3.0 – v3.0.0)
**Theme**: Robustness through SQLite persistence and a strict 4-layer modular structure.

*   **SQLite Migration**: Fully decommissioned CSV and local JSON files for core data. Implemented **SQLite in WAL (Write-Ahead Logging) mode** for superior concurrency and state persistence.
*   **Strategy Engine**: Centralized signal logic into a rule-based engine. Established the boundary where the Engine generates signals and the AI *explains* them, preventing AI "hallucination" in trading signals.
*   **Unified Assistant**: Consolidated Research and Reports into a single, high-performance page with deterministic caching and responsive AI insight containers.
*   **The 4-Layer Standard**: Finalized the current architectural standard:
    1.  **Presentation (Dash)**: UI and Callbacks.
    2.  **Service (Business Logic)**: Data fetching and formatting.
    3.  **Engine (Math/AI)**: Quantitative and qualitative intelligence.
    4.  **Data (Repository)**: SQLite persistence.

---

## Phase 6: Professionalization & UI Refinement (v3.1.0 – v3.5.0)
**Theme**: Polishing the visual experience and ensuring system-wide compliance.

*   **Deep Dive Visualization Fix**: Solved persistent "grey canvas" artifacts in Treemaps by harmonizing Plotly backgrounds with CSS surface tokens and implementing theme-aware typography for hierarchical data.
*   **Portfolio Suggestions**: Integrated the Strategy Engine directly into the main Holdings table, providing instant BUY/SELL/HOLD signals alongside live P&L data.
*   **UI Standardization**: Enforced a strict **16px/24px global grid** and centralized all content wrappers into a single `section()` helper to ensure layout consistency across all pages.
*   **Intraday Resiliency**: Refined the "Today" view with 5-minute resampling, Plotly `rangebreaks` to hide non-trading hours, and a 15:00 lookback window for cross-session continuity.
*   **Compliance Audit**: Executed a 100% precision audit of the codebase, standardizing logging to use `logger.debug()` (replacing `print`) and verifying `prevent_initial_call=True` for all page-specific callbacks.

---

## Phase 7: Rendering Prioritization & UX Polish (v3.6.0 – v3.7.0)
**Theme**: Optimizing for extreme responsiveness, visual stability, and aesthetic excellence.

*   **Fast Startup Architecture**: Refactored the core application lifecycle to eliminate blocking market data fetches during initialization. The dashboard now boots instantly (<1s) using disk-cached state, with live data refreshing in the background after the UI is interactive.
*   **Rendering Prioritization**: Implemented a URL-aware callback strategy that eliminates "DOM thrashing" and UI flicker. By making rendering callbacks aware of the active page, the browser only updates visible components, significantly reducing CPU load during high-frequency market updates.
*   **UI Stabilization & Skeletons**: Integrated brand-aligned, pulsing skeleton loaders across all data-bound containers. Developed **fixed-column grid skeletons** to eliminate "layout shift" where the UI would jump or stack vertically before data arrived.
*   **Persistent Chart State (uirevision)**: Implemented stable `uirevision` keys across all major visualizations. This ensures that 5-minute background data refreshes do NOT reset user zoom, pan, or toggles, creating a seamless "tracking" experience.
*   **Live Tracking Aesthetics**: Applied 300ms CSS transitions to all key financial metrics. Data updates now smoothly ease into place, mimicking the fluid feel of high-end fintech dashboards.
*   **Standardized Empty States**: Introduced a centralized chart fallback system (`create_empty_fig`) to ensure all visualizations maintain a professional aesthetic during loading or error states.

---

## Phase 8: Aesthetic Excellence & Chart Standardization (v3.8.0 – Current)
**Theme**: Standardizing the visual language and achieving "Linear-grade" UI polish.

*   **Unified Chart Architecture**: Refactored the entire charting library to use a centralized `apply_standard_layout` helper. This enforced a single source of truth for **Inter 10px** typography, unified hover models, and grid opacities across all 15+ dashboard visualizations.
*   **Glassmorphism Navigation**: Implemented a frosted-glass navigation bar with `backdrop-filter: blur(12px)` and semi-transparent layers, optimized for high-performance rendering in WebKit (Safari).
*   **Theme Transition Smoothness**: Eliminated jarring visual snaps by implementing **200ms CSS transitions** on all theme-aware properties (background-color, color, border-color) across the entire application shell.
*   **Data Freshness Pulse**: Introduced a live "heartbeat" indicator in the header. The animated status dot pulses green during market hours and remains static grey otherwise, providing at-a-glance evidence of live monitoring.
*   **Interactive Depth & Typography**: Standardized on **Inter with tabular numerals** for financial accuracy and added interactive hover states (lift + teal glow) to all dashboard cards.

---

## Phase 9: Performance Baseline & Multi-Tier Intervals (v3.9.0 – Current)
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



---

## Phase 7: Distribution, Packaging & Setup UX (v2.4.0)
**Theme**: Making Folio installable by anyone directly from GitHub — no Python expertise required.

*   **uv-Based Installer**: Replaced the manual `pip install` setup process with a two-script installer (`install.sh` for macOS/Linux, `install.bat` for Windows). The installers use [uv](https://docs.astral.sh/uv/) to automatically download and configure Python 3.12, create an isolated `.venv`, install all dependencies, and install the Playwright WebKit browser — all in a single command.
*   **macOS App Bundle**: `install.sh` generates a native `Folio.app` bundle in the project root. The bundle contains an `Info.plist` and a shell launcher that resolves paths relative to its location, allowing it to be moved to `/Applications` or pinned to the Dock.
*   **Windows Launcher**: `install.bat` generates a `folio_launch.bat` shortcut in the `scripts/` folder after install, which can be pinned to the Start menu or Taskbar.
*   **Interactive API Key Setup**: The installer interactively prompts for a Gemini API key during setup and writes it to `.env` automatically, eliminating the manual copy-and-edit step for new users.
*   **Zero Source Code Changes**: No Python source files were modified. The app continues to use the project directory for all data (`data/portfolio.db`, `data/cache/`) and the existing `.env` for secrets, exactly as in development mode.
*   **README Overhaul**: Replaced the single "Setup" section with a comprehensive "Installation" section covering macOS (with `.app` instructions), Windows (with `.bat` instructions), Linux, API key configuration, and a separate Developer Setup path for contributors.
*   **scripts/ Subdirectory Installers**: Organized installers (`scripts/install.command` for macOS/Linux, `scripts/install.bat` for Windows) inside the `scripts/` folder, keeping the project root clean and clutter-free, while remaining fully double-clickable directly from Finder/Explorer.
*   **Automated Desktop Shortcuts**: Implemented automated desktop shortcut generation (`Folio.command` on macOS Desktop; `Folio.lnk` on Windows Desktop via PowerShell) so the user has immediate access to run the app with one click from their desktop.
*   **Resilient Virtual Environment Reuse**: Refactored the environment setup process to check for and reuse existing `.venv/` folders, preventing installation crashes on subsequent runs or app updates.
*   **Safe Permission Fallbacks**: Implemented graceful error catching during file copy operations (such as macOS `Desktop/` write permissions), warning the user to copy shortcuts manually rather than failing the installer.
*   **Browser Auto-Launch with Port Polling**: Configured the Windows launcher to check port 8050, wait for the Dash server to initialize, and automatically open the application in the user's default browser (matching the macOS experience).
*   **Detailed Setup Troubleshooting Guide**: Appended a comprehensive "Troubleshooting & Common Setup Issues" section to the README, detailing workarounds for macOS Gatekeeper blocks, Windows execution policy limits, directory path spacing, and Cloud sync locks.

---

## Phase 8: Browser-Close Graceful Shutdown (v2.5.0)
**Theme**: Lifecycle integration — the app process mirrors the browser window's lifetime.

*   **`beforeunload` Beacon**: Added `assets/browser_shutdown.js`, which registers a `window.beforeunload` listener and fires `navigator.sendBeacon('/shutdown?token=<TOKEN>')` when the user closes the tab or window. `sendBeacon` is used (not `fetch`) because it is guaranteed to dispatch even as the page tears down.
*   **3-Second Server Debounce**: A new Flask route `/shutdown` (registered on `app.server`) validates a shared one-time secret token and starts a `threading.Timer(3.0)` before sending `SIGTERM` to its own process. The delay prevents false positives on hard refreshes.
*   **SPA Navigation Cancel**: `browser_shutdown.js` intercepts `history.pushState`, `history.replaceState`, and `popstate` to fire `navigator.sendBeacon('/shutdown/cancel')` immediately on any Dash internal navigation. The Flask `/shutdown/cancel` route aborts the countdown if still running, so navigating between pages or refreshing the app **never** triggers a shutdown.
*   **Per-Run Secret Token**: `secrets.token_urlsafe(16)` generates a unique token at each app startup. It is embedded into the rendered HTML via a `<meta name="shutdown-token">` tag (injected through a new `get_index_string(token)` helper in `components/portfolio_layout.py`), so the JS can read it without any network round-trip.
*   **Launcher Compatibility**: When running via `launcher.py`, the SIGTERM from the Dash process causes the launcher's heartbeat loop to detect a non-zero exit code and call its existing `handle_exit()`, which gracefully terminates the background worker and exits the terminal. No changes to `launcher.py` were required.
*   **Files Changed**: `assets/browser_shutdown.js` (new), `app.py` (token generation + Flask routes), `components/portfolio_layout.py` (template function).

---

## Phase 11: Layman-Friendly Documentation & Onboarding Guidance (v2.6.0)
**Theme**: Standardizing documentation for ultimate clarity, lay-man accessibility, and detailed local developer/user guide mapping.

*   **Lay-Man Friendly Explanations**: Overhauled the root `README.md` to introduce the core concept of Folio using real-world analogies, making it clear for beginners.
*   **Finance-to-English Dictionary**: Added simple definitions of tickers, ETFs, P&L (intraday and total), transactions, ex-dividend dates, Sharpe Ratio, volatility, correlation, and forecasting.
*   **Local Double-Process Flowchart**: Built a clear ASCII mapping demonstrating the interactive relationship between the Browser UI, Dash Web App, Background Worker, and local relational SQLite database (`portfolio.db`).
*   **Bulletproof Setup & OS Troubleshooting**: Documented the installation process step-by-step for macOS and Windows, explaining what the installer scripts configure (uv, Python 3.12, WebKit Playwright, .env Gemini keys). Added direct solutions for permission privileges, macOS Gatekeeper blocks, Windows PowerShell policies, and cloud syncing database locks.
*   **Complete Workspace Reference**: Included a comprehensive folder map outlining the exact responsibility and location of all pages, callbacks, components, services, database queries, and testing suites.
