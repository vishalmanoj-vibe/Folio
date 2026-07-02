# Current Build Tasks Archive

> Back to [GEMINI.md](../../GEMINI.md)

This document contains the archive of completed build tasks, moved here from [GEMINI.md](../../GEMINI.md) to keep the core rules lightweight.

---

### Refresh Intervals & Caching Architecture (Complete)
- Live Price / P&L: Updates globally every 300s (5 minutes).
- Technical Signals (RSI/MACD): 24h cache (`TECHNICALS_CACHE_TTL`).
- Dividend Data: 7d cache (`DIVIDENDS_CACHE_TTL`).
- AI Weekly Report: Manual trigger only via Reports page.

### Strategy Engine & AI Analyst (Complete)
- `services/strategy_engine.py` — Weighted scoring (Trend 0.35, Momentum 0.20, Price vs 200MA 0.15, Price vs Cost 0.15, Risk 0.15).
- `services/ai_engine.py` — Analyst overlay with caching, safe JSON parsing, tone mapping, and fallback.
- `services/market/data_fetcher.py` — Added `get_full_history_cache()` and `extract_close()` public helpers.
- `callbacks/signals_callbacks.py` — Manual trigger callbacks for both portfolio and watchlist; registered in `app.py`.
- `app.py` — Added `signals-store` and `watchlist-signals-store` (both session storage, seeded empty).
- `pages/positions.py` — "Generate Signals" button with `dcc.Loading` status label.
- `callbacks/positions_callbacks.py` — Signal badges in card grid; AI Insight card in detail panel.

### Watchlist Signal Extension (Complete)
- `components/watchlist_layout.py` — "Generate Signals" button + `dcc.Loading` status label added to page header.
- `callbacks/watchlist_callbacks.py` — Signal badge column added to watchlist table; AI Insight card appended to stat cards.
- `callbacks/signals_callbacks.py` — `generate_watchlist_signals_callback` added (uses `watchlist-store` holdings as synthetic holding dicts).
- `app.py` — `watchlist-signals-store` (session) seeded alongside `signals-store`.

### Portfolio Suggestion Extension (Complete)
- `callbacks/portfolio_callbacks.py` — Added "Suggestion" column to main holdings table.
- Column position: Inserted before "Div yield".
- Data source: Integrated `signals-store` (populated from Positions page) as State input to prevent redundant renders.
- UI: Coloured signal badges (BUY/SELL/HOLD) rendered with `_signal_badge_td` helper.

### AI Engine & UI Stabilization (Complete)
- `services/ai_engine.py` — Removed invalid `request_options` (SDK incompatibility) and stabilized cache keys by ignoring volatile live price ticks to minimize API costs.
- `pages/positions.py` & `components/watchlist_layout.py` — Added dedicated `ai-insight-container` to isolate AI insights from the CSS Grid, preventing metric card shrinking.
- `callbacks/positions_callbacks.py` & `callbacks/watchlist_callbacks.py` — Updated typography for AI explanations (readable 13px font) and themed technical scores in teal (`var(--cyan)`).
- `callbacks/watchlist_callbacks.py` — Adjusted price chart Y-axis to dynamically zoom to period lows instead of forcing $0, improving data visibility for high-priced stocks.

### Dividend Consolidation & UI Standardization (Complete)
- `services/market/dividend_service.py` — Centralized all dividend math (realized income, projections, trend data) into a single service layer.
- `pages/positions.py` — Merged the "Dividend Dashboard" into the Positions page. Redundant top-level summary strips and standalone dividend pages were removed.
- `assets/layout.css` — Standardized global page-header and section padding to a uniform `16px 24px` grid.
- **Dynamic Container Pattern**: Refactored the Positions and Watchlist pages to use dynamic containers (`positions-price-chart-container`, etc.) that hide headers and empty states until a ticker is selected, ensuring a clean "Day 1" UI.
- `components/ui_helpers.py` — Established `section()` as the primary structural wrapper for all dashboard content to enforce consistent margins and borders.- **Relational Migration (Complete)**: Transitioned from CSV/JSON to SQLite for all identity and state data. Implemented WAL mode for concurrency and a 7-day persistent cache for ETF metadata.

### Intraday Chart Refinement (Complete)
- `services/market/market_status.py` — Added `get_previous_trading_session_start()` to calculate a 15:00 lookback window (skipping weekends).
- `services/market/session_cache.py` — Implemented 290s cooldown for snapshots and backfill logic with timezone-aware alignment.
- `components/charts/pnl_history.py` — Implemented 5-minute resampling and Plotly `rangebreaks` to hide overnight sessions. Updated hover labels to include full date context.
- `services/market/data_fetcher.py` — Updated `fetch_live` to request 2-day windows and ensure snapshots/backfills occur even on internal cache hits.

- **Project-wide Audit**: Standardized all services to use `logger.debug()` and verified correct `prevent_initial_call` usage (False/initial_duplicate for rendering, True for interactions) for multi-page safety.
### Rendering Prioritization & Fast Startup (Complete)
- **Callback Prioritization**: Implemented `pathname` awareness across all rendering callbacks in `chart_callbacks.py`, `positions_callbacks.py`, and `watchlist_callbacks.py` to prevent off-page DOM thrashing.
- **Fast Startup**: Refactored `app.py` to seed `portfolio-store` and `watchlist-store` with disk cached data, removing blocking `fetch_live` calls from the startup sequence.
- **Standardized Fallbacks**: Integrated `create_empty_fig` across all chart components to ensure professional empty states.
- **Aesthetic Excellence & Chart Standardization (Complete)**:
- Unified all charts via `apply_standard_layout()` for consistent typography and hover UX.
- Implemented glassmorphism nav bar and 200ms theme transitions.
- Added real-time animated market status heartbeat to the header.

### Memory Hygiene & Dual-Process Architecture (Complete)
- `launcher.py` — New process manager separating Dash UI from background data processing.
- `worker.py` — Background worker handling technical analysis, signals, and market refreshes.
- `services/market/data_fetcher.py` — Implemented metadata truncation and compact series caching.
- `core/cache.py` — Enforced bounded memory caching with automated eviction passes.
- **History Gating**: Enforced 24h staleness for historical data to eliminate redundant network churn.

### Watchlist Drag & Drop Reordering (Complete)
- **Database Migration**: Added `order_index` column (default 0) to `watchlist` table in SQLite (`portfolio.db`) automatically migrating existing systems on startup.
- **Repository Integration**: Enabled ordering by `order_index ASC, added_date ASC` on loading, dynamic next index calculation on adding, and implemented `update_watchlist_order(ticker_order)` under a clean transactional block with connection hygiene.
- **Draggable UI Layout**: Added premium grab handle (`☰`) column. Enabled row `draggable="true"`, custom `data-ticker` attributes, and glassmorphic dragging states in CSS resets.
- **HTML5 Event Delegation Engine**: Added `assets/drag_drop.js` with document-level event delegation (survives Dash complete DOM refreshes) to reorder row elements locally and notify Python callbacks via a hidden `#watchlist-order-input` dcc.Input component.

### High-Performance Isolated Testing Framework (Complete)
- **Unified Test Runner**: Implemented `scratch/run_tests.sh` to dynamically handle virtualenv environments, offline pytest triggers, and HTML/XML coverage reporting.
- **Isolated Mocks**: Developed 9 mock-isolated unit test suites located strictly in `scratch/tests/` evaluating 61 core test cases spanning Repositories, Services, Technical Indicators, and UI callbacks without live network or external database requests.
- **Quality & Pre-Commit Hooks**: Configured mypy types (`mypy.ini`) and ruff lints to check code structure and format as an automated Git pre-commit barrier.

### NEW Features 
- **Feature 1: Dynamic Ticker-Aware Command Palette**:
  - Populated `palette-ticker-store` with grouped holding/watchlist metadata and active strategy signals via a clientside callback.
  - Upgraded `assets/command_palette.js` to parse these dynamic groups and enable keyboard navigation (CMD+K) and selection.
- **Feature 2: Portfolio Day-Change Heatmap**:
  - Enabled "Day Change" option on segmented control on the Analytics page.
  - Implemented the heatmap treemap mode with diverging red/green color scaling based on day change percent.
- **Feature 3: Investor Profile Settings Page**:
  - Implemented the settings page `/settings` with Dropdowns for Investment Goal, Risk Tolerance, and Tax Bracket, saved to a SQLite `user_settings` table.
  - Added dynamic weight previews (Trend, Momentum, Value, Cost, Risk) on goal/risk selection.
  - Embedded profile settings into technical signal generation in `worker.py` and research assistant prompt context in `research_service.py`.
- **Feature 5: News Sentiment Score Overlay**:
  - Integrated news sentiment analysis (Positive/Neutral/Negative, and score float) using DDGS news search and Gemini scoring, cached for 24h.
  - Triggered news sentiment automatically in signal generation batch refreshes in the background worker.
  - Rendered colored sentiment score columns on the main portfolio table and watchlist table.
