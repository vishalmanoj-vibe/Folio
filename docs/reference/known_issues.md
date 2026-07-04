# Known Issues — Folio
## "Never Repeat This" Bug Registry

> These are confirmed, production bugs that have already been fixed.
> This document exists to prevent regression. Before touching any related code,
> read the relevant entry here first.

---

## BUG-001 · Plotly `update_layout` TypeError (Silent White Chart)

**Status**: Fixed  
**Files affected**: Any chart builder in `components/charts/`  
**Symptom**: Chart renders as a stark white grid; no visible Python error, but browser console shows a 500.

**Root Cause**:
Unpacking `**PLOTLY_BASE` (a dict) alongside a conflicting kwarg like `margin` causes a `TypeError` in Plotly's `update_layout`. Dash catches the exception silently and renders a blank default chart.

```python
# ❌ BROKEN — duplicate 'margin' key causes TypeError
fig.update_layout(**PLOTLY_BASE, margin=dict(t=10, b=10))

# ✅ FIXED — copy first, then override
layout_args = PLOTLY_BASE.copy()
layout_args["margin"] = dict(t=10, b=10)
fig.update_layout(**layout_args)
```

**Prevention**: `apply_standard_layout()` in `components/charts/helpers.py` handles this pattern correctly. Always use it instead of calling `update_layout` directly.

---

## BUG-002 · Pattern-Matching "Ghost" Click

**Status**: Fixed  
**Files affected**: `callbacks/watchlist_callbacks.py` (remove button callback)  
**Symptom**: Dynamic table rows trigger their own removal callback immediately on creation, deleting themselves before the user interacts.

**Root Cause**:
Dash fires `n_clicks=0` when a pattern-matched component (e.g. `{"type": "watchlist-remove-btn", "index": ticker}`) is first inserted into the DOM. This bypasses `prevent_initial_call=True`, which only prevents the *very first* app load, not subsequent DOM insertions.

```python
# ❌ BROKEN — fires on render with n_clicks=0
@app.callback(Output(...), Input({"type": "watchlist-remove-btn", "index": ALL}, "n_clicks"))
def remove_ticker(n_clicks_list):
    # THIS RUNS ON RENDER with [0, 0, 0, ...]

# ✅ FIXED — gate on actual click
if not ctx.triggered or not ctx.triggered[0]["value"] or ctx.triggered[0]["value"] <= 0:
    return dash.no_update
```

**Prevention**: Every pattern-matched button callback MUST validate `ctx.triggered[0]["value"] > 0` before acting.

---

## BUG-003 · `scaleanchor` Y-axis Misalignment (Candlestick Chart)

**Status**: Fixed  
**Files affected**: `components/charts/` (any chart using multiple Y axes)  
**Symptom**: Volume bars render overlapping the price candles; chart proportions look wrong.

**Root Cause**:
Setting `scaleanchor` or `scaleratio` on a secondary Y-axis while also setting `domain` causes Plotly to ignore the `domain` and recompute the axis range from the anchor, producing misaligned panels.

**Fix**: Never combine `scaleanchor` with `domain`. Use `domain` exclusively to define subplot areas:

```python
# ✅ Correct multi-axis layout
fig.update_layout(
    yaxis=dict(domain=[0.25, 1.0]),           # Price panel: top 75%
    yaxis2=dict(domain=[0.0, 0.20], ...),     # Volume panel: bottom 20%
    # NO scaleanchor here
)
```

---

## BUG-004 · `dcc.Loading` Spinner Never Fires

**Status**: Fixed  
**Files affected**: `pages/positions.py`, `components/watchlist_layout.py`  
**Symptom**: A loading spinner wrapping a button never shows during a long-running callback.

**Root Cause**:
`dcc.Loading` animates only when one of its **direct children** is the `Output` target of a callback. Wrapping the **Input** trigger (a button) has no effect.

```python
# ❌ WRONG — wraps the Input, never fires
dcc.Loading(children=dmc.Button("Generate", id="my-btn"))

# ✅ CORRECT — wraps the Output target
dmc.Button("Generate", id="my-btn"),
dcc.Loading(
    type="dot",
    children=html.Span(id="my-status-label")  # ← this is the Output
)
```

---

## BUG-005 · Intelligence Chart Blank on Forecast Toggle

**Status**: Fixed  
**Files affected**: `callbacks/intelligence_callbacks.py`, `components/charts/`  
**Symptom**: The equity forecast chart goes blank when the user toggles the forecast switch.

**Root Cause**:
`uirevision=True` (a static value) tells Plotly to preserve the user's view state (zoom, pan). When the forecast toggle removes the forecast trace and changes the X-axis range, Plotly "helpfully" restores the old range (which extends into the future), making it appear that no data exists.

```python
# ❌ BROKEN — uirevision never changes, stale range preserved
fig.update_layout(uirevision=True)

# ✅ FIXED — uirevision changes when toggle changes, forcing a re-render
fig.update_layout(uirevision=f"pred_{pred_on}")
```

---

## BUG-006 · Interval-Triggered Chat Reset

**Status**: Fixed  
**Files affected**: `callbacks/research_callbacks.py`  
**Symptom**: Chat conversation history is wiped every 30 seconds.

**Root Cause**:
Using `Input("portfolio-store", "data")` to initialise the chat store means the callback re-fires on every portfolio refresh interval, resetting the conversation.

**Fix**: Use `Input("url", "pathname")` for page-init callbacks. Guard against re-initialisation:

```python
@app.callback(
    Output("research-chat-store", "data"),
    Input("url", "pathname"),
    State("research-chat-store", "data"),
    prevent_initial_call=True,
)
def init_chat(pathname, current_history):
    if pathname != "/research":
        return dash.no_update
    if current_history:  # Guard: don't overwrite existing conversation
        return dash.no_update
    return [{"role": "model", "content": "How can I help?"}]
```

---

## BUG-007 · `dmc.Button` `leftIcon` / `rightIcon` Removed in v2

**Status**: Fixed  
**Files affected**: Any layout file using `dash-mantine-components`  
**Symptom**: `TypeError: The dash_mantine_components.Button component received an unexpected keyword argument: leftIcon`

**Fix**: Renamed in dmc v2 to align with Mantine 7:
- `leftIcon` → `leftSection`
- `rightIcon` → `rightSection`

---

## BUG-008 · MultiIndex Column Extraction Failure

**Status**: Fixed  
**Files affected**: Any service that calls `yf.download()` for multiple tickers  
**Symptom**: `KeyError` or `AttributeError` when accessing price columns from a yfinance bulk download.

**Root Cause**:
`yf.download()` for multiple tickers returns a `(Metric, Ticker)` MultiIndex column structure. Accessing `df["Close"]` fails or returns a DataFrame instead of a Series.

**Fix**: Use public helpers only. Never import private `_extract_col`:
```python
from services.market.data_fetcher import extract_close, get_full_history_cache

# ✅ Correct
close_series = extract_close(df, "CBA.AX")  # Returns pd.Series
```

---

## BUG-009 · yfinance Returns 0.0 Price During ASX Off-Hours

**Status**: Fixed  
**Files affected**: `services/market/data_fetcher.py`  
**Symptom**: Portfolio P&L shows $0 or NaN for all ASX positions outside trading hours.

**Root Cause**:
`fast_info.last_price` returns `0.0` when the market is closed. This propagates through the entire P&L calculation.

**Fix**:
```python
price = ticker_obj.fast_info.last_price
if not price or price == 0.0:
    # Fallback: use most recent historical close
    hist = ticker_obj.history(period="2d")
    price = hist["Close"].iloc[-1] if not hist.empty else 0.0
```

---

## BUG-010 · Gemini API `request_options` SDK Incompatibility

**Status**: Fixed  
**Files affected**: `services/ai_engine.py`  
**Symptom**: `TypeError` on AI analysis calls; requests never complete.

**Root Cause**: The Gemini Python SDK does not accept a `request_options` kwarg in `generate_content()`. Passing it causes an immediate crash.

**Fix**: Remove `request_options` entirely. Implement timeout logic at the `try/except` level instead.

---

## BUG-011 · Backend Memory Thrashing via task-poll-interval Feedback Loop

**Status**: Fixed  
**Files affected**: `callbacks/chart_callbacks.py`  
**Symptom**: RAM usage on landing page balloons from 200MB to 1.2GB.

**Root Cause**: Wrapping a heavy graph generation callback (like `pnl_history_chart`) with a high-frequency polling trigger `Input("task-poll-interval", "n_intervals")` causes the entire chart to rebuild every 2 seconds when any background task is running. This creates massive pandas and Plotly figure allocations that Python's memory manager cannot reclaim fast enough.

**Fix**: Decouple the chart callback from the polling trigger. Create an ultra-lightweight status checker callback to handle polling database benchmarks and only update `benchmark-pending-store`. Have the chart callback listen only to changes in data stores (`portfolio-store` and `benchmark-pending-store`), preventing unnecessary high-frequency rebuilds.

---

## BUG-012 · MutationObserver Cascade Feedback Loop (Browser Tab Freeze)

**Status**: Fixed  
**Files affected**: `assets/sync_hover.js`, `assets/countup.js`  
**Symptom**: Browser tab chews up high CPU and memory, sometimes freezing.

**Root Cause**: Setting `MutationObserver` on `document.body` with `{ childList: true, subtree: true }` intercepts every DOM update. Because Plotly rendering generates hundreds of minor DOM updates during creation, the observer fires continuously. If the observer callback queries the DOM and unbinds/re-binds event listeners (or updates text node content), it creates an infinite feedback loop of mutations.

**Fix**:
1. Filter added nodes in the observer to ensure they match target selectors (e.g. `.js-plotly-plot`) before acting.
2. Add debouncing (e.g. 100ms) to event-listener setup calls to avoid re-triggering during a single render sweep.
3. Observe only specific, relevant mutations (avoid broad `characterData` and `childList` observation of `document.body` simultaneously when updating inner text).


---

## BUG-013 · Missing Previous-Day Lookback in Intraday P&L Chart (1d)

**Status**: Fixed  
**Files affected**: `components/charts/pnl_history.py`, `services/market/data_fetcher.py`  
**Symptom**: Today's P&L chart starts exactly at 10:00 AM of the current session, missing the final hour (15:00 onwards) of the previous trading day for context. On weekends or closed market periods, the previous day hour scale is rendered but no data points are plotted for it (appearing empty).

**Root Cause**:
1. Chart Builder: Refactoring for offline context normalization hardcoded `chart_start` to `effective_start.replace(hour=10)`. This completely excluded previous session points from database querying and filtered them out of the Plotly rendering range.
2. Data Backfill: `fetch_live()` called `get_previous_trading_session_start()` without arguments. On weekends (e.g. Saturday), this returns Friday at 15:00. However, the chart's effective date on weekends is Friday, which expects lookback data starting from Thursday at 15:00. The backfill only loaded data from Friday at 15:00 onwards, causing the previous day section of the weekend chart to remain blank.

**Fix**:
Both the chart builder and the data fetcher backfill logic must resolve the previous trading day starting point relative to the timezone-aware `effective_date` or `effective_start` date:

```python
# ✅ Correct Lookback Start Calculation relative to effective context
from services.market.market_status import get_previous_trading_session_start
chart_start = get_previous_trading_session_start(relative_to=effective_start)
```

---

## BUG-014 · P&L and Normalized Price Chart Axis Auto-scaling Blocked by uirevision

**Status**: Fixed  
**Files affected**: `components/charts/pnl_history.py`, `components/charts/price_history.py`  
**Symptom**: Changing the chart period filters (e.g. from "max" to "1y") updates the data correctly but doesn't adjust the x-axis and y-axis scale. The chart only resets and scales properly when the browser page is hard refreshed.

**Root Cause**:
Plotly's `uirevision` parameter preserves the user's view state (zoom, pan, axis ranges) across updates. Since `apply_standard_layout()` hardcoded a static `uirevision=True`, Plotly "helpfully" preserved the previous view state's axis ranges even when the active period was changed.

**Fix**:
Make `uirevision` dynamic so it changes whenever a filter that affects the date range or metric units changes. By including the selected ticker, the period, and the value/percentage mode in the revision key, Plotly will re-calculate optimal scales whenever these change, while still preserving zoom/pan during background live data refreshes:

```python
# ❌ BROKEN — static uirevision prevents re-scaling when period/mode changes
fig.update_layout(uirevision=True)

# ✅ FIXED — uirevision changes when active filters change, forcing axis re-scale
fig.update_layout(uirevision=f"{selected}_{period}_{mode}")
```

---

## BUG-015 · Appending Memory Summaries Duplication

**Status**: Fixed  
**Files affected**: `services/research_memory.py`  
**Symptom**: The Welcome message of the Assistant shows multiple stacked, duplicate "Here's a summary of the investment research conversations" sections that grow indefinitely over time.

**Root Cause**:
The startup maintenance process previously cleaned up expired conversation turns (older than 7 days) and generated a summary chunk for them. However, it simply appended this new block to the existing summary file using string concatenation (`combined = existing + "\n\n" + new_summary_chunk`), leading to a compounding list of duplicate headers and bullet points.

**Fix**:
Updated `summarise_old_turns` to accept the `existing_summary` as an optional parameter. When present, the prompt instructs the Gemini model to perform an intelligent merge, returning a single, unified, consolidated summary (3-5 bullet points) instead of appending. Added a self-healing check in `run_startup_maintenance` to automatically detect and consolidate any stacked legacy summaries upon application startup.

---

## BUG-016 · Ticker Suffix Corruption & Missing Display Name Merge

**Status**: Fixed  
**Files affected**: `app.py`, `callbacks/transaction_callbacks.py`, `data/cache_manager.py`, `services/market/data_fetcher.py`, `data/database.py`  
**Symptom**: Adding a new ticker with `.ax` or `.AX` suffix (e.g. `URNM.ax`) does not update its long name in the main holdings table, and fails to populate the Positions detail panel and Analytics price charts.

**Root Cause**:
1. **Suffix Corruption**: Transaction submission callbacks in `app.py` and `transaction_callbacks.py` did not normalize user input tickers, saving them as `URNM.AX`. The holdings aggregation engine `build_holdings` appended `.AX` unconditionally, producing `URNM.AX.AX` which broke all yfinance downloads.
2. **Missing Name Merging**: The central `get_live_prices` query selected strictly from the `market_prices` table (which does not store names) and omitted a join with the `assets` metadata table. Thus, the name field fell back to a hardcoded constants list.
3. **Blanked OHLC Fields**: `save_live_prices` omitted `prev_close`, `day_high`, and `day_low` columns during `INSERT OR REPLACE` operations, causing these columns to be reset to `NULL` upon every refresh.

**Fix**:
1. Normalize user inputs by stripping trailing `.AX` / `.ax` (case-insensitive) in all transaction submission and ticker discovery callbacks.
2. Formally declare `prev_close`, `day_high`, and `day_low` in `market_prices` schema/migrations, and write them in `save_live_prices`.
3. Add a `LEFT JOIN assets a ON mp.ticker = a.ticker` to `get_live_prices` queries to fetch long names, and merge them in `load_portfolio_snapshot` for the holdings table.

---

## BUG-017 · Plotly `branchvalues="total"` Validation Failure (Blank Treemap)

**Status**: Fixed  
**Files affected**: `components/charts/treemap.py`  
**Symptom**: The treemap visual does not render (displays a blank screen or console errors) when trying to view hierarchical layouts like Underlying Holdings.

**Root Cause**:
When using `branchvalues="total"`, Plotly strictly validates that the value of each parent node matches exactly the sum of its children nodes. Minor floating-point rounding discrepancies or incomplete mocked data weights in unit tests (where weights sum to less than 100%) violate this validation rule, causing Plotly to fail rendering the entire figure.

**Fix**:
1. Ensure the mock weights in unit tests always sum to exactly 100%.
2. In the chart builder code, calculate the value of the last child node dynamically as the residual of the parent's value minus the sum of the previous children's values (`val = parent_val - sum(previous_child_vals)`). This guarantees that the sum matches the parent's value exactly, even in the presence of floating-point inaccuracies.

---

## BUG-018 · `UnboundLocalError` on Positions & Watchlist Pages for New Tickers

**Status**: Fixed  
**Files affected**: `callbacks/positions_callbacks.py`, `callbacks/watchlist_callbacks.py`  
**Symptom**: Navigating to `/positions` or `/watchlist` fails to load metrics and detail elements, showing an infinite loading spinner. Python logs show `UnboundLocalError: local variable 'tech_signals' referenced before assignment`.

**Root Cause**:
When a new ticker is added to the portfolio or watchlist, it has no cached historical price data in the database, resulting in an empty history series. The callback checks `if not history_s.empty:` to build the technical signal badges, but if it is empty, the `tech_signals` variable is never assigned, leading to an `UnboundLocalError` during the return statement.

**Fix**:
Initialize `tech_signals = None` before fetching and checking the close series:
```python
# ✅ FIXED — always define tech_signals to avoid UnboundLocalError
tech_signals = None
history_s = HistoryRepository().load_close_series(ticker, ...)
if not history_s.empty:
    tech_signals = tech_signal_badges(ticker, history_s)
```

---

## BUG-019 · Page Load Deadlock / Freeze on Refresh & Direct Load

**Status**: Fixed  
**Files affected**: `callbacks/positions_callbacks.py`, `callbacks/watchlist_callbacks.py`  
**Symptom**: Navigating directly to `/positions` or `/watchlist` (or reloading the page on those routes) causes the UI to freeze indefinitely on loading spinners/skeletons. The python logs show HTTP 200 without any exception stack traces.

**Root Cause**:
To prevent background rendering when on other pages, page-specific callbacks used `prevent_initial_call=True`. However, when refreshing the page, the selected ticker value is loaded from browser session storage. Because this value is already set, the selection callback doesn't detect a value change, preventing downstream callbacks from firing. Combined with `prevent_initial_call=True`, the rendering callbacks never execute during initial layout paint, leaving the page frozen in loading states.

**Fix**:
Change `prevent_initial_call=False` on the page-specific rendering callbacks, and ensure they are all protected by a page pathname guard (e.g. `if url_pathname.rstrip('/') != '/positions': return dash.no_update`) to prevent background off-page rendering.

---

## BUG-020 · Server Shutdown on Full Page Reload or Standard Link Navigation

**Status**: Fixed  
**Files affected**: `assets/browser_shutdown.js`  
**Symptom**: Navigating to page routes using standard `html.A` links (such as clicking "Investor Profile") or performing a full page refresh causes the Dash app server process to crash and close after 3 seconds.

**Root Cause**:
The window-close detection script (`browser_shutdown.js`) sends a `/shutdown` beacon on `beforeunload` events to initiate a 3-second server termination countdown. While it intercepted internal Dash SPA navigations (such as `pushState` / `replaceState` / `popstate`) and sent a `/shutdown/cancel` beacon, it failed to send a cancel beacon on script load/initialization. Consequently, any full page reload or standard `html.A` link navigation triggered the shutdown beacon, but since no SPA navigation event fired during page load, the server countdown was never aborted, causing the server process to terminate.

**Fix**:
Add an automatic cancel beacon trigger upon script execution / DOM load to cancel any pending shutdown timers:
```javascript
// Cancel any pending shutdown on script load (handles full page refresh / page GET)
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", sendCancelBeacon);
} else {
    sendCancelBeacon();
}
```

---

## BUG-021 · Settings Revert to Defaults on Page Load

**Status**: Fixed  
**Files affected**: `callbacks/settings_callbacks.py`  
**Symptom**: Opening the Settings page displays default values (e.g. 37% tax bracket, Balanced goal, moderate risk) instead of the user's previously saved options. If the user clicks Save, these defaults overwrite their actual preferences in the database.

**Root Cause**:
The settings loading callback `load_user_settings` was configured with `prevent_initial_call=True`. Because navigating to Settings (via standard `html.A` links) acts as an initial layout paint, Dash suppressed the callback from running on startup. As a result, the form fell back to the hardcoded default values defined in the page layout.

**Fix**:
Change `prevent_initial_call=False` on the settings rendering/hydration callbacks to ensure they execute on initial page paint, while retaining pathname guards (e.g. `if pathname != "/settings": return dash.no_update`) to prevent background off-page rendering.

---

## BUG-022 · Benchmark Chart Fails to Load Custom/Preferred Benchmark Indices

**Status**: Fixed  
**Files affected**: `data/cache_manager.py` (`get_benchmarks_db`), `callbacks/chart_callbacks.py`  
**Symptom**: Selecting a non-default benchmark index (like Nasdaq 100 or a custom ticker) fails to display its line trace on the holdings chart. The chart remains loaded with only S&P 500 and ASX 200.

**Root Cause**:
`get_benchmarks_db()` checked only if the database table `benchmark_data` was empty or if the timestamp was stale (> 24h). If the database already had the default S&P 500 and ASX 200 records cached from startup, it returned that dictionary. Because the return value was not `None`, the chart rendering callback bypassed enqueuing a background fetch task (`fetch_benchmarks`), leaving the new index completely missing from the cache.

**Fix**:
Modify `get_benchmarks_db()` to read the user's current benchmark preferences from settings. If the user's preferred index symbol is missing from the cached database records, return `None` immediately. This triggers the Dash UI callback to enqueue a background fetch task to pull the missing index via yfinance.

---

## BUG-023 · Empty Browser Page After Onboarding Restart

**Status**: Fixed  
**Files affected**: `callbacks/setup_callbacks.py` (clientside `pollServer`)  
**Symptom**: After clicking "Restart and Launch Dashboard", the browser navigates to `/` but the page is blank — no layout, no data.

**Root Cause**:  
The `pollServer` function polled `GET /` (the Flask root route). Flask's WSGI layer responds with HTTP 200 as soon as the Flask server is bound and listening — **before** Dash has finished registering all pages, callbacks, and the layout. The browser therefore arrived at `/` while Dash was still initialising its callback graph, producing an empty render.

**Fix Pattern**:
Poll `/_dash-layout` instead of `/`. This Dash-internal endpoint is only registered and returns 200 **after** the Dash application object has fully initialised all layouts. This is a reliable sentinel for "Dash is ready".  
Add a `1s` post-confirmation delay before `window.location.href = '/'` to allow the new process's `startup-interval` to fire first.  
Increase initial shutdown wait from `2500ms` to `3500ms` to account for Python multiprocess cold-start time.

```js
// ❌ BROKEN — Flask responds before Dash is ready
fetch('/' + cacheBuster)

// ✅ FIXED — only 200s after Dash has fully initialised
fetch('/_dash-layout' + cacheBuster)
    .then(response => {
        if (response.status === 200) {
            setTimeout(function() { window.location.href = '/'; }, 1000);
        }
    })
```

**Prevention**: Any future restart/reload polling must target `/_dash-layout`, never the root path.

