# Skill: Debug Dash

This skill captures diagnosis steps and specific edge cases discovered while building the Portfolio Dashboard.

## Diagnosis Steps

### 1. Classify the error
Identify which layer the error is in:
- **Data layer**: `data/`, `services/market/`
- **Engine layer**: `core/engine/portfolio_engine.py`
- **Callback**: `callbacks/`
- **Layout**: `components/layout.py` or `pages/`
- **Market data**: `yfinance` fetch in `services/market/data_fetcher.py`

### 2. Common root causes
- **Multi-page ID Errors**: Dash fires callbacks for IDs not in the current layout. Fix: Add `prevent_initial_call=True`.
- **yfinance 0.0 Price**: ASX off-hours return 0.0. Fix: Fallback to historical close.
- **MultiIndex Extraction Failure**: `yf.download` returns (Ticker, Metric) columns. Fix: Use `_extract_col` helper.
- **Timezone Gaps**: Ensure all processing uses `Australia/Sydney`.
- **CSS Loading**: Variables must be in `base.css` to load first.

## Specific Edge Cases & Technical Debt

### 1. Plotly `update_layout` TypeError Crash
**Symptom**: A chart renders as a stark white default grid; silent 500 error in browser.
**Cause**: Unpacking `**PLOTLY_BASE` alongside conflicting kwargs (like `margin`). Dash silently aborts the update.
**Solution**: Copy the base dictionary and override keys before unpacking:
```python
layout_args = t_["PLOTLY_BASE"].copy()
layout_args["margin"] = dict(t=10, b=10, l=10, r=10)
fig.update_layout(**layout_args)
```

### 2. Dash Pattern-Matching "Ghost" Clicks
**Symptom**: Dynamic elements (like table rows) trigger removal callbacks immediately upon creation.
**Cause**: Dash fires `n_clicks=0` when a matching component is first rendered, bypassing `prevent_initial_call`.
**Solution**: Strictly validate `n_clicks > 0` before acting:
```python
if ctx.triggered and ctx.triggered[0]["value"] and ctx.triggered[0]["value"] > 0:
    # Proceed with action
```

### 3. Intelligence Chart uirevision Bug
**Symptom**: Chart goes blank when toggling the prediction switch.
**Cause**: `uirevision=True` preserves the forced future X-axis range even when data is removed.
**Solution**: Change `uirevision` string when toggle changes:
```python
eq_fig.update_layout(uirevision=f"pred_{pred_on}")
```
