# Technical Spec — Incremental Signal Generation & Real-time Stream Fill

## Feature Summary
Currently, generating signals processes all tickers in bulk and only updates SQLite and the Dash UI `signals-store` once every ticker is finished. For portfolios with 10–20 holdings, this results in a long delay (20–30s) where the UI remains frozen on "Updating Intelligence...". This feature enables incremental processing and real-time UI streaming: as each ticker's signal and AI analysis completes in the background worker, it is committed to SQLite immediately and streamed to `signals-store` / `watchlist-signals-store` during active polling cycles.

## Modified Files
- `worker.py` — Update `handle_generate_signals` to process each ticker end-to-end (Strategy Engine → AI Engine → SQLite commit) and save results incrementally after each ticker rather than in bulk at the end.
- `callbacks/signals_callbacks.py` — Update `poll_tasks_and_update_stores` to read available signal results from SQLite whenever a task is in `running` or `complete` status, emitting store updates incrementally if new ticker data is present.

## Component IDs
No new Dash component IDs introduced. Utilises existing:
- `signals-store`
- `watchlist-signals-store`
- `pending-tasks-store`
- `task-poll-interval`
- `global-signals-status-label`

## Data Strategy & Store Contracts
- Stores affected: `signals-store` and `watchlist-signals-store`.
- JSON shape remains strictly compliant with `docs/reference/store_contracts.md`:
  `{"raw": {<ticker>: ...}, "ai": {<ticker>: ...}, "generated_at": "<timestamp>"}`
- Partial state handling: During generation, the `raw` and `ai` dictionaries will incrementally gain keys as tickers complete. UI callbacks (`render_card_grid`, `render_watchlist_table`) already handle dictionary lookups safely using `.get(ticker)`.

## Resolved Pain Points (Ideator & PM Review)
1. **Unnecessary UI Re-renders**: Polling every 2s while task is `running` could fire duplicate store updates even when no new ticker finished.
   - *Solution*: Store updates are only emitted if the newly read SQLite records contain more tickers or updated timestamps compared to the existing store data state. If unchanged, returns `dash.no_update`.
2. **Hysteresis State Continuity**: Calculating hysteresis for tickers sequentially could miss previous signal context.
   - *Solution*: `prev_signals` map is initialized from DB upfront and updated in memory as each ticker completes.
3. **Fault Tolerance / Partial Failure**: An error in AI analysis or data for Ticker #3 could abort the remaining tickers.
   - *Solution*: Per-ticker processing is wrapped in a `try/except` block. If a single ticker fails, an error signal record is stored for that ticker, and the loop safely proceeds to subsequent tickers.
4. **Data Depth Pre-fetch**: Fetching historical prices per ticker sequentially would be slow yfinance overhead.
   - *Solution*: Keep the bulk `get_full_history_cache` and missing depth `fetch_portfolio_series` check at the start of `handle_generate_signals` before starting the per-ticker processing loop.

## Fallback States
- Empty / No Tickers: Returns `{"raw": {}, "ai": {}}` immediately.
- Partial Loading: Tickers that haven't finished processing yet will have no entry in `signals-store["raw"]`, causing UI components to render default neutral badges until their signal streams in.
- Single Ticker Error: Saved with error reason, allowing other tickers to complete and display successfully.

## Verification Plan
1. Trigger global intelligence refresh from header or page button.
2. Observe backend worker logs confirming incremental `INSERT OR REPLACE INTO signal_results` commits per ticker.
3. Confirm Dash UI cards and badges fill out one by one as signals are completed, rather than all at once.
4. Verify task completes cleanly and status label transitions to "Updated HH:MM".
