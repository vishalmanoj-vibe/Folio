# Build Log — Permanent Server Readiness & Browser Launch Fix

## Summary of Changes Made
1. **[`launcher.py`](../../launcher.py)**:
   - Added `_wait_and_open_browser(self)` thread that actively polls `http://127.0.0.1:8050/` until `HTTP 200 OK` is returned.
   - Safari / default browser is opened at the exact millisecond port 8050 becomes responsive.
   - Prevents duplicate browser openings on process restart or headless mode.
2. **[`scripts/Folio.command`](../../scripts/Folio.command)**:
   - Removed fixed 30s/45s `sleep` loops and `osascript` browser calls from bash.
   - Streamlined script to delegate readiness verification and browser launching to `launcher.py`.
3. **[`scripts/install_shortcut.py`](../../scripts/install_shortcut.py)**:
   - Created installer script to simplify updating `~/Desktop/folio.command`.

---

# Build Log — Incremental Signal Generation & Real-time UI Streaming

**Date**: 2026-08-12  
**Scope**: Progressive signal fill-out on Positions and Watchlist pages

## Files Changed

### `worker.py` — `handle_generate_signals()`
- **Before**: Strategy engine was called once on all tickers (`generate_portfolio_signals(multi_full, holdings, ...)`), AI analysis called once on all results, then a single bulk `INSERT OR REPLACE` + `conn.commit()` for all tickers at the end.
- **After**: Each holding is processed end-to-end in a per-ticker loop: Strategy Engine → AI Engine → `INSERT OR REPLACE` + `conn.commit()` per ticker. Sentiment fetch also runs per-ticker.
- `prev_signals` map is built upfront from DB and updated in-memory after each ticker so hysteresis state is correctly threaded through the sequential run.
- Per-ticker processing wrapped in `try/except` so a single failing ticker does not abort the batch.
- Previous bug fixed: `prev_signals` previously always queried `signal_results` table even for watchlist scope; now correctly queries `watchlist_signal_results` for watchlist scope.

### `callbacks/signals_callbacks.py` — `poll_tasks_and_update_stores()`
- **Before**: Only updated `signals-store` / `watchlist-signals-store` when task status == `"complete"`.
- **After**: Also reads and streams partial results when task status == `"running"`. Added `State("signals-store", "data")` and `State("watchlist-signals-store", "data")` to the callback signature for change detection.
- Change detection: new data is only written to the store if `new_ticker_count > current_ticker_count`. This prevents redundant DOM re-renders on poll intervals where no new ticker has been committed.

## New Component IDs
None — no new Dash component IDs introduced.

## Output IDs Modified
No new Output IDs added. Existing Output IDs unchanged:
- `signals-store` — still owned by `signals_callbacks.py`
- `watchlist-signals-store` — still owned by `signals_callbacks.py`
- `pending-tasks-store` — unchanged
- `refresh-trigger-store` — unchanged

