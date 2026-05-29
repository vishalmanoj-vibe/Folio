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
