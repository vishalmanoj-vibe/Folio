# Project Rules — Folio

## ⚡ READ THIS FIRST — Required Read Order

**Step 0 — Refresh the auto-generated indexes (always do this first):**

```bash
python3 .agents/generated/sync_docs.py
```

This regenerates `.agents/generated/callback_index.md` and `.agents/generated/store_index.md` from the live codebase. Run it before reading anything else — the indexes must reflect the current state of the code, not a stale snapshot.

Then read these documents **in order**:

0. **`.agents/project_map.md`** — Navigation index. Find which doc and which file to look at for any task.
1. **`.agents/skills/registry.md`** — Component ID registry. Check for ID collisions before writing any layout.
2. **`docs/reference/callback_ownership.md`** — Output ownership map. Verify the Output ID is not already owned before adding a callback. For exact line numbers, also check `.agents/generated/callback_index.md`.
3. **`docs/reference/store_contracts.md`** — Exact JSON shapes for `portfolio-store`, `signals-store`, `watchlist-store`. Never guess the shape.
4. **`docs/reference/known_issues.md`** — Bug registry. If you're touching a chart, callback, or store, confirm you're not re-introducing a known bug.
5. **This file (GEMINI.md)** — Architecture rules. Read the relevant section for what you're changing.
6. **The specific file you're editing** — Read the full function/callback before changing any line.

> Skipping steps 1–4 is the single biggest source of regressions in this project.

---

## Stack
- Python 3.12.13, Dash (multi-page), Plotly, yfinance, pandas
- Entry: app.py → pages/ (portfolio.py, etf_detail.py, intelligence.py)
- Data: SQLite (`portfolio.db`) → `database.py` → `repository.py` → `fetch_live()`
- All chart figures live in components/charts/ and return go.Figure
- Callbacks are modular: core, chart, transaction, alert, ui, positions, dividend, insights, watchlist, research, report, signals
## Architecture — never break these
- Do NOT modify app.py layout or the two dcc.Store seeds (txn-store, portfolio-store)
- All new chart callbacks go in callbacks/chart_callbacks.py
- New pages must register_callbacks(app) and be imported in app.py after app creation
- **Multi-page Safety**: Rendering callbacks targeting page-specific elements MUST use `prevent_initial_call=False` (or `"initial_duplicate"` if duplicate outputs are present) to ensure they fire on initial page navigation/load. Button/interaction callbacks (like click/submit handlers) should use `prevent_initial_call=True` to prevent premature execution.
- **Prioritized Rendering**: Every rendering callback MUST include `Input("url", "pathname")` and return `dash.no_update` if the pathname does not match the callback's target page. This prevents background re-render flicker.
- **Dynamic Layouts**: All pages MUST define layout as a callable function (`def layout():`) rather than a static variable to ensure proper component ID registration on every page load.
- **Period Sync**: The `portfolio-store` refresh callback in `app.py` must sync with page-specific period stores (`positions-period-store`, `watchlist-period-store`, etc.) to ensure the global data fetch covers the maximum requested period.
- **Three-Interval Pattern**: Standardized for all pages to ensure responsiveness:
  - `startup-interval` (1.5s): Triggers the first data fetch after page paint.
  - `heartbeat-interval` (30s): Drives real-time UI badges and status indicators.
  - `price-interval` (300s): Performs heavy market data refreshes (MUST be gated by `is_market_open()`).
- All pages MUST use the `create_header` component for navigation consistency
- CSS vars only: var(--t-pri), var(--t-sec), var(--bg), var(--surface), var(--border), var(--green), var(--red)
- Never hardcode hex colors in Python layout code
- Modular CSS: New styles must be added to appropriate assets/ files (base, components, vendor, etc.). Monolithic styles.css is prohibited.
- Asset Loading: Dash loads assets alphabetically. Variables and resets (base.css) must load before overrides (vendor.css).
- **Relational Persistence**: All core data (transactions, assets, watchlist, metadata) MUST be stored in `portfolio.db`. Never use CSVs for production state.
- **SQLite Concurrency**: Always enable `PRAGMA journal_mode = WAL` and `busy_timeout = 5000` in `get_connection()`.
- **Explicit Closure**: Every database connection MUST be explicitly closed using `finally: conn.close()` or equivalent to prevent resource leaks.
- **Intraday Stability**: 
  - 290s cooldown enforced in `session_cache.py` to prevent jagged data from frequent fetch triggers.
  - All intraday charts (`pnl_history.py`) MUST apply 5-minute resampling (`resample('5min').last().ffill()`) to ensure visual uniformity.
  - X-axis `rangebreaks` MUST be used to hide non-trading hours (16:15 - 10:00) and weekends for seamless session stitching.
- **Chart Fallbacks**: Every chart figure builder MUST implement a fallback to `create_empty_fig()` from `components.charts.helpers` if data is missing or invalid. AX axes/grid artifacts are prohibited.
- **Chart Standardization**: All charts MUST use the `apply_standard_layout()` helper to ensure unified typography (Inter 10px), grid opacity, and hover label consistency.
- **Fast Startup**: `app.py` MUST NOT perform blocking yfinance fetches during initialization. It must seed stores with disk snapshots and defer the first live refresh to a `startup-interval`.
- **Measurement Hygiene**: `@profile` decorators from `memory_profiler` are strictly PROHIBITED in application code outside of `scripts/`. They must be removed immediately after debugging.
- **Lazy Dependencies**: Heavy libraries (e.g. `prophet`, `playwright`) MUST be imported lazily inside the function body that requires them, never at the module level, to ensure fast application startup.
- **Dynamic Sleep**: Background threads must use `time_until_market_open()` for sleep scheduling to prevent idle CPU cycles during weekends and market off-hours.
- **Memory Hygiene**: 
  - `portfolio-store` MUST NEVER contain historical price arrays. It only stores holdings metadata and live metrics.
  - `fetch_live()` returns only `{holdings, fetched_at}`. Histories are excluded to keep JSON payloads < 20KB.
  - All history access MUST go through `HistoryRepository` (SQLite) or `fetch_ticker_history()` (Lazy).
  - Heavy DataFrames (e.g. `multi_full` from yfinance) MUST NOT be stored in long-term cache. Extract compact `pd.Series` and discard the raw DataFrame immediately.
- **Distributed Scraping**: All heavy provider scrapes (Playwright/Scraping) MUST be offloaded to the background worker. The Dash process is strictly read-only for holdings metadata.
- **Depth Awareness**: The `is_stale` check for 'max' periods MUST check if a 'max' fetch has already been performed to prevent infinite refresh loops for young tickers with < 220 days of history.
- **Staleness Gating**: Enforce a strict 24-hour staleness gate for all historical (non-live) price data.

## Data conventions
- Tickers stored without .AX in CSV; ticker_yf = ticker + ".AX" for yfinance
- Price fallback: use historical close when fast_info returns 0.0 (ASX off-hours)
- yfinance: always use yf.download() bulk — never per-ticker calls in a loop
- **Intraday Lookback**: Daily (1d) charts fetch `period="2d"` at `interval="5m"` to include the final hour (15:00 onwards) of the previous trading session for trend context.
- **Market Status**: `is_market_open` supports `include_auction=True` (16:15 close) for backend data collection and `include_auction=False` (16:00 close) for UI status badges.
- All MultiIndex column extraction must use public helpers — never import private `_extract_col` from other service files:
  - `extract_close(df, ticker_yf)` → returns a `pd.Series` of Close prices for one ticker
  - `get_full_history_cache(holdings)` → returns the full bulk MultiIndex DataFrame from cache
- **OHLC Extraction**: `services/market/data_fetcher.py` extracts Open, High, Low, and Close columns for historical data to support Candlestick charts on the Positions page.

## Technical Indicators
- All technical indicator math lives in `services/technical_indicators.py`.
- Pure pandas implementation: No external libraries like `pandas_ta` or `talib` should be used for core math to maintain portability.
- RSI: Use `ewm(com=period-1)` to match industry standard (Wilder's RSI).
- MACD: Returns `(macd_line, signal_line)` as a tuple.
- Bollinger Bands: Returns `(upper, mid, lower)` as a tuple.
- Signals: `compute_signals()` returns a standardized dict with 10 keys: `ticker`, `rsi`, `rsi_label`, `macd`, `macd_signal`, `macd_label`, `bb_upper`, `bb_lower`, `bb_label`, `last_price`.

## Scraper Architecture
- **Three-Tier Architecture**: The application uses a robust scraper for ETF Holdings data (`holdings_fetcher.py`).
  - Tier 1: Direct CSV/JSON API calls (`requests`).
  - Tier 1.5: DuckDuckGo Search (DDGS) URL discovery with a 5s timeout.
  - Tier 2: Headless WebKit Playwright fallback.
- **Manual Setup Required**: The host system MUST manually install Playwright via `pip install playwright && playwright install webkit`. The application will not automatically install it.
- **Strict Process Management**: All browser sessions MUST be wrapped in `try/finally` blocks to guarantee `browser.close()` and prevent memory leaks.
## When making changes
- Read the relevant callback file before touching it — don't guess at existing IDs
- **Path Finding**: Use `grep -r` to locate the exact file and function before editing. Never guess a path. See `.agents/skills/surgical_edit.md` for grep patterns.
- **Skills First**: When a task matches a skill in `.agents/skills/`, read that skill file before writing code. Skills contain tested patterns — use them instead of reinventing.
- **Known Issues Gate**: Before touching a chart builder, pattern-matched callback, or store callback, read `docs/reference/known_issues.md` to confirm you are not re-introducing a known bug.
- Preserve all existing Dash component IDs exactly
- If adding a new chart: add figure builder in components/charts/, wire in chart_callbacks.py
- If adding a store: seed it at startup in app.py alongside txn-store
- Run python app.py to verify — never assume the app still starts
- **Performance**: Always update `docs/performance/` templates after running performance measurement phases.
- **Test Code Revision**: If a diagnostic or test script fails to run due to an error, always revise and repair the existing file instead of creating a new one.

## Do not
- Never use position: fixed in Dash layouts
- Never import pages before app = dash.Dash(...) is created
- Never call yfinance per-ticker in a loop — use bulk download
- Never hardcode AEST offset — use pytz or zoneinfo for timezone checks
- **Hex in Callbacks**: Never pass CSS `var()` strings to Python functions that perform math on colors (like `interpolate_color`). Use hardcoded hex values from `config/constants.py` for these cases.
- **Theme Context**: All rendering callbacks that generate Plotly charts MUST take `Input("theme-store", "data")` and pass it to `get_theme(theme or "dark")`. Do not call `get_theme()` without arguments to avoid missing positional argument errors.
- **UI Transitions**: All theme-aware elements (body, cards, nav) MUST have a 200ms CSS transition on `background-color`, `color`, and `border-color` to prevent jarring theme snaps.
- **Data Freshness**: The header status indicator MUST accurately reflect `is_market_open(include_auction=False)` with a pulsing green dot during trading and a static grey dot otherwise.
- **Diagnostic/Test Scripts**: All diagnostic, test, benchmark, or throwaway scripts and code MUST be saved exclusively in the `scratch/` folder to prevent codebase clutter and directory pollution.

## Self-Improvement
- After every task, evaluate if a new Rule or Skill should be added to the `.agents/` directory to prevent repeating mistakes or to codify successful new patterns.

## Context Document Maintenance — After Every Build

After completing any task that adds, removes, or renames a component:

**Always update (no approval needed — factual changes only):**
- `docs/reference/callback_ownership.md` — add any new Output IDs with their owning callback file. Remove entries for deleted outputs.
- `.agents/skills/registry.md` — add any new component IDs introduced.

**Append only if a new bug pattern was discovered and fixed:**
- `docs/reference/known_issues.md` — one entry per bug: root cause, affected file, fix pattern. Never edit existing entries.

**Never auto-update (require explicit instruction):**
- `docs/reference/store_contracts.md` — store shapes only change intentionally. A wrong auto-update here breaks all consumers silently.
- `GEMINI.md` itself — architectural rules require human judgment.

> **The update is part of the task. A build is not complete until the relevant context documents reflect the current state of the code.**

- **Rule-Based Engine** (`services/strategy_engine.py`): Single source of truth for signals. Never override with AI output.
- **AI Assistant** (`services/ai_engine.py`): Sits *after* the engine. Explains and critiques signals only — does NOT generate them.
- **Signals Stores**: Two session-scoped `dcc.Store`s — one per context. Never cross-wire them.
  - `signals-store` — Portfolio holdings (Positions page). Triggered by `generate-signals-btn`.
  - `watchlist-signals-store` — Watchlist tickers. Triggered by `watchlist-generate-signals-btn`.
- **Manual Trigger Only**: Signal generation is always user-initiated. Never wire either signals store to `live-interval`.
- **Watchlist Holdings**: Watchlist tickers use synthetic holding dicts (`avg_cost=0`, `buy_tranches=[]`). The strategy engine handles these gracefully — cost-dimension scoring is skipped, no CGT warnings are emitted.
- **AI Skip Threshold**: Skip AI analysis when `abs(score) < 0.4`. Always return a safe default dict — never return `None` or omit the key.
- **AI Verdict Normalisation**: All AI verdicts must pass through `VERDICT_MAP` in `ai_engine.py`. Hardcoded to three values: `Confident`, `Mixed`, `Risk flagged`.
- **Tone Sanitisation**: `_sanitize_tone()` must be applied to all AI explanation and risk strings before storage.
- **Deterministic Caching**: Cache key = `"ai_signal_" + md5(json.dumps(stable_signals, sort_keys=True))`. Stable signals exclude volatile live prices to prevent redundant API calls. TTL = 86400s (24h).
- **Signal Boundaries**: BUY >= 0.5, SELL <= -0.5, HOLD otherwise. No dead zones.
- **Hysteresis**: Signal flip prevented when `abs(new_score) < 0.7`. Always set `hysteresis_forced: bool` on output.
- **CGT Warnings**: Injected into SELL signal `reasons` list when any tranche has been held < 1 year.
- **Private Helper Rule**: Do NOT import `_extract_col` (private) from `data_fetcher` into other service files. Use `get_full_history_cache()` (public) instead.
- **No print() in services**: Use `logger.debug()` for strategy output, not `print()`.

## Current Build Tasks Archive

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

## Minimal Edit Mode — Default for All Changes

> **Default behaviour**: Every edit MUST be minimal. Only change the exact lines required to fix the bug or add the feature. Assume everything around the target is correct and tested.

### Do Not Touch Zones

These areas are frozen. **Do NOT modify them unless the user explicitly names them in their request.**

| Zone | File | Reason |
|------|------|---------|
| App layout scaffold | `app.py` lines 176–242 | Store seeds and interval registration. Changing breaks all pages. |
| `txn-store` writer | `app.py` `update_txn_store()` | Single owner. Adding a second writer causes data corruption. |
| `portfolio-store` writer | `app.py` `update_portfolio_store()` | Single owner. Side-effect writes cause race conditions. |
| CSS variable definitions | `assets/base.css` | Load order is alphabetical; variables must exist before any component uses them. |
| `apply_standard_layout()` | `components/charts/helpers.py` | Shared by all charts. Changing it breaks every chart simultaneously. |
| `create_header()` | `components/header.py` | Shared singleton. Changing breaks global nav on all pages. |
| `get_connection()` | `data/database.py` | WAL mode + busy_timeout must stay. Removing breaks SQLite concurrency. |
| Signal boundary constants | `services/strategy_engine.py` | BUY ≥ 0.5, SELL ≤ −0.5. Do not adjust thresholds without explicit instruction. |
| `VERDICT_MAP` | `services/ai_engine.py` | Hardcoded to 3 values. Adding values breaks normalisation logic. |
| Store IDs | anywhere | Never rename a `dcc.Store` ID — it breaks all consuming callbacks silently. |

### Minimal Edit Checklist

Before submitting any edit, confirm:
- [ ] I read the file before editing it
- [ ] I changed only the specific function/block that is broken
- [ ] I did not touch any Do Not Touch Zone
- [ ] I did not rename any component ID, variable, or function signature
- [ ] I did not add imports outside the edited block
- [ ] I ran `ruff check <file> --fix && ruff format <file>`

---

## Surgical Edit Rules — NEVER violate these

- NEVER rewrite a file. Only edit the specific function or block that is broken.
- NEVER change a function signature unless explicitly asked.
- NEVER remove a function, callback, or import unless explicitly asked.
- NEVER reorganise imports or reformat code outside the edited block.
- NEVER rename variables, IDs, or class names.
- Before editing any file, state exactly which lines you are changing and why.
- If fixing a bug requires touching more than 2 files, STOP and ask for approval first.
- After every edit, list what you changed and confirm what you did NOT change.

## Code Quality Rule
After every file edit, run `ruff check <filename> --fix` 
and `ruff format <filename>` before considering the task complete.
Fix any ruff errors before finishing. Never leave unused imports
or undefined names in edited files.