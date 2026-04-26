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

### 4. Gemini API Context Injection Pattern
**Symptom**: AI gives generic responses that ignore the user's portfolio.
**Cause**: Portfolio context was stored in the history list, causing it to
grow stale and eventually be truncated by token limits.
**Solution**: Always prepend context to the LAST user message only, on every
call. Never store context inside the history list:
```python
messages_to_send = history.copy()
context = build_portfolio_context(portfolio_data, ticker)
messages_to_send[-1]["content"] = context + "\n\n" + messages_to_send[-1]["content"]
response = model.generate_content(...)
```
This keeps history clean and ensures every call has fresh portfolio data.

### 5. Gemini GenerativeModel Chat vs generate_content
**Symptom**: Multi-turn conversation loses context after first reply.
**Cause**: Using model.generate_content() for multi-turn chat instead of
the chat session pattern.
**Solution**: For multi-turn conversations use the messages list pattern
with roles explicitly set to "user" and "model" (not "assistant"):
```python
# Gemini uses "model" not "assistant" for the AI role
history_for_gemini = [
    {"role": "model" if m["role"] == "assistant" else "user",
     "content": m["content"]}
    for m in history[:-1]  # all but last message
]
```

### 6. Preventing Interval-Triggered Chat Resets
**Symptom**: Chat history is wiped every 30 seconds when the portfolio
interval refresh fires, resetting mid-conversation.
**Cause**: Using `Input("portfolio-store", "data")` as the trigger for a
page-init callback means the callback re-fires on every periodic refresh.
**Solution**: Use `Input("url", "pathname")` instead of
`Input("portfolio-store", "data")` for initialisation callbacks on
specific pages. Guard against re-initialisation by checking if the
current state already exists before writing:
```python
@app.callback(
    Output("research-chat-store", "data"),
    Input("url", "pathname"),
    State("portfolio-store", "data"),
    State("research-chat-store", "data"),
    prevent_initial_call=True,
)
def init_page_chat(pathname, portfolio_data, current_history):
    if pathname != "/research":
        return no_update
    # Guard: do not overwrite an existing conversation
    if current_history is not None and len(current_history) > 0:
        return no_update
    # ... build welcome message
```