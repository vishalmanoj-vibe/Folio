# Skill: Debug Dash

## Objective
Diagnose and fix errors in the portfolio dashboard without
introducing regressions to existing functionality.

## Rules of Engagement
- Never guess — always read the file before editing it
- Never change a component ID to fix a bug
- If the fix touches a callback, check all its Inputs and Outputs first
- Run python app.py after every fix attempt

## Diagnosis Steps

### Step 1 — Classify the error
Identify which layer the error is in:
  A) Data layer    → data/, services/market/
  B) Engine layer  → core/engine/portfolio_engine.py
  C) Callback      → callbacks/
  D) Layout        → components/layout.py or pages/
  E) Market data   → yfinance fetch in services/market/fetcher.py

### Step 2 — Common root causes (check these first)
- Callback fires before store is seeded → add prevent_initial_call=True
- Chart is blank → holdings list is empty, add guard: if not holdings: return go.Figure()
- yfinance returns 0.0 price → ASX off-hours; check price fallback logic in fetcher.py
- MultiIndex column error → use _extract_close() helper, never direct column access
- CSS not applying → check var(--t-pri) etc. are defined in body[data-theme] in layout.py INDEX_STRING
- Import error → pages must be imported AFTER app = dash.Dash(...) in app.py

### Step 3 — Fix and verify
1. Read the broken file fully before editing
2. Make the minimal change that fixes the root cause
3. Run: python app.py
4. Confirm the specific error is gone
5. Briefly describe what the root cause was and what changed

### Step 4 — Report
State:
  - Root cause (one sentence)
  - What file(s) changed
  - What to watch for (any related fragile areas)