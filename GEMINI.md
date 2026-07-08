# Project Rules — Folio

## ⚡ READ THIS FIRST — Required Read Order

**Step 0 — Refresh the auto-generated indexes (always do this first):**

```bash
python3 .agents/generated/sync_docs.py
```

This regenerates `.agents/generated/callback_index.md` and `.agents/generated/store_index.md` from the live codebase. Run it before reading anything else — the indexes must reflect the current state of the code, not a stale snapshot.

Then read these documents **in order**:

0. **[`.agents/project_map.md`](.agents/project_map.md)** — Navigation index. Find which doc and which file to look at for any task.
1. **[`.agents/skills/registry.md`](.agents/skills/registry.md)** — Component ID registry. Check for ID collisions before writing any layout.
2. **[`docs/reference/callback_ownership.md`](docs/reference/callback_ownership.md)** — Output ownership map. Verify the Output ID is not already owned before adding a callback. For exact line numbers, also check [`.agents/generated/callback_index.md`](.agents/generated/callback_index.md).
3. **[`docs/reference/store_contracts.md`](docs/reference/store_contracts.md)** — Exact JSON shapes for `portfolio-store`, `signals-store`, `watchlist-store`. Never guess the shape.
4. **[`docs/reference/known_issues.md`](docs/reference/known_issues.md)** — Bug registry. If you're touching a chart, callback, or store, confirm you're not re-introducing a known bug.
5. **This file ([`GEMINI.md`](GEMINI.md))** — Architecture rules. Read the relevant section for what you're changing.
6. **The specific file you're editing** — Read the full function/callback before changing any line.

> Skipping steps 1–4 is the single biggest source of regressions in this project.

---

## Stack
- Python 3.12.13, Dash (multi-page), Plotly, yfinance, pandas
- Entry: app.py → pages/ (portfolio.py, positions.py, watchlist.py, intelligence.py, analytics.py, settings.py)
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
- **Absolute Paths**: Never include absolute paths (e.g. pointing to local user directories like `file:///Users/...`) in any documentation or spec files. Use relative links instead.

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

See [build_tasks_archive.md](docs/history/build_tasks_archive.md) for the historical list of completed build tasks, extracted to maintain lightweight architectural rules.

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