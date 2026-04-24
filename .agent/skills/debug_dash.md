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
- **Multi-page ID Errors** → Dash fires callbacks for IDs not in the current layout.
  - *Fix*: Add `prevent_initial_call=True` to ALL page-specific callbacks.
- **yfinance 0.0 Price** → ASX off-hours (AEST) return 0.0 for last price.
  - *Fix*: Check if `fast_info['last_price'] == 0` and fallback to `hist['Close'].iloc[-1]`.
- **MultiIndex Extraction Failure** → Bulk downloads (`yf.download`) return (Ticker, Metric) columns.
  - *Fix*: Use `_extract_close(df)` helper or `.xs('Close', axis=1, level=1)`.
- **Timezone Gaps** → ASX data is AEST. Mixed timezones cause "missing" today data.
  - *Fix*: Ensure all market data processing uses `pytz.timezone('Australia/Sydney')`.
- **CSS Alpha Loading** → Dash loads assets alphabetically.
  - *Fix*: Variables must be in `base.css` (A-first) to ensure they are available to others.
- **Dividend Mismatch** → Yahoo Finance ex-dates can be inconsistent for ASX ETFs.
  - *Fix*: Reference `CONFIRMED_PAYOUTS` in `dividend_service.py` for VHY/IOZ.
- **F-string component crashes** → Complex Python layout strings with `{}` inside list comprehensions.
  - *Fix*: Break complex component generation into standalone helper functions.

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