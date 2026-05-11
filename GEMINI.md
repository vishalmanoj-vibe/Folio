# Project Rules — Folio

## Stack
- Python 3.11, Dash (multi-page), Plotly, yfinance, pandas
- Entry: app.py → pages/ (portfolio.py, etf_detail.py, intelligence.py)
- Data: SQLite (`portfolio.db`) → `database.py` → `repository.py` → `fetch_live()`
- All chart figures live in components/charts/ and return go.Figure
- Callbacks are modular: core, chart, transaction, alert, ui, positions, dividend, insights, watchlist, research, report, signals
## Architecture — never break these
- Do NOT modify app.py layout or the two dcc.Store seeds (txn-store, portfolio-store)
- All new chart callbacks go in callbacks/chart_callbacks.py
- New pages must register_callbacks(app) and be imported in app.py after app creation
- **Multi-page Safety**: ALL callbacks targeting page-specific elements MUST use `prevent_initial_call=True`.
- **Prioritized Rendering**: Every rendering callback MUST include `Input("url", "pathname")` and return `dash.no_update` if the pathname does not match the callback's target page. This prevents background re-render flicker.
- **Dynamic Layouts**: All pages MUST define layout as a callable function (`def layout():`) rather than a static variable to ensure proper component ID registration on every page load.
- **Period Sync**: The `portfolio-store` refresh callback in `app.py` must sync with page-specific period stores (`positions-period-store`, `watchlist-period-store`, etc.) to ensure the global data fetch covers the maximum requested period.
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

## When making changes
- Read the relevant callback file before touching it — don't guess at existing IDs
- Preserve all existing Dash component IDs exactly
- If adding a new chart: add figure builder in components/charts/, wire in chart_callbacks.py
- If adding a store: seed it at startup in app.py alongside txn-store
- Run python app.py to verify — never assume the app still starts

## Do not
- Never use position: fixed in Dash layouts
- Never import pages before app = dash.Dash(...) is created
- Never call yfinance per-ticker in a loop — use bulk download
- Never hardcode AEST offset — use pytz or zoneinfo for timezone checks
- **Hex in Callbacks**: Never pass CSS `var()` strings to Python functions that perform math on colors (like `interpolate_color`). Use hardcoded hex values from `config/constants.py` for these cases.
- **UI Transitions**: All theme-aware elements (body, cards, nav) MUST have a 200ms CSS transition on `background-color`, `color`, and `border-color` to prevent jarring theme snaps.
- **Data Freshness**: The header status indicator MUST accurately reflect `is_market_open(include_auction=False)` with a pulsing green dot during trading and a static grey dot otherwise.

## Self-Improvement
- After every task, evaluate if a new Rule or Skill should be added to the `.agent/` directory to prevent repeating mistakes or to codify successful new patterns.

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

- **Project-wide Audit**: Standardized all services to use `logger.debug()` and verified `prevent_initial_call=True` for multi-page safety.
- **Page Renaming**: Standardized page names to Holdings, Positions, Watchlist, Insights, Deep Dive, and Assistant.

### Rendering Prioritization & Fast Startup (Complete)
- **Callback Prioritization**: Implemented `pathname` awareness across all rendering callbacks in `chart_callbacks.py`, `positions_callbacks.py`, and `watchlist_callbacks.py` to prevent off-page DOM thrashing.
- **Fast Startup**: Refactored `app.py` to seed `portfolio-store` and `watchlist-store` with disk cached data, removing blocking `fetch_live` calls from the startup sequence.
- **Standardized Fallbacks**: Integrated `create_empty_fig` across all chart components to ensure professional empty states.
- **Aesthetic Excellence & Chart Standardization (Complete)**:
  - Unified all charts via `apply_standard_layout()` for consistent typography and hover UX.
  - Implemented glassmorphism nav bar and 200ms theme transitions.
  - Added real-time animated market status heartbeat to the header.
