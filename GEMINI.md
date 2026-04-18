# Project Rules — portfolio_dashboard

## Stack
- Python 3.11, Dash (multi-page), Plotly, yfinance, pandas
- Entry: app.py → pages/ (portfolio.py, etf_detail.py, intelligence.py)
- Data: CSV → csv_handler.py → portfolio_builder.py → fetch_live()
- All chart figures live in components/charts/ and return go.Figure
- Callbacks are modular: core, chart, transaction, alert, ui

## Architecture — never break these
- Do NOT modify app.py layout or the two dcc.Store seeds (txn-store, portfolio-store)
- All new chart callbacks go in callbacks/chart_callbacks.py
- New pages must register_callbacks(app) and be imported in app.py after app creation
- CSS vars only: var(--t-pri), var(--t-sec), var(--bg), var(--surface), var(--border)
- Never hardcode hex colors in Python layout code

## Data conventions
- Tickers stored without .AX in CSV; ticker_yf = ticker + ".AX" for yfinance
- Price fallback: use historical close when fast_info returns 0.0 (ASX off-hours)
- yfinance: always use yf.download() bulk — never per-ticker calls in a loop
- All MultiIndex column extraction must use _extract_close() helper

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