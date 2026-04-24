# Build Log: Automatic Dividend Tracking

## Date: 2026-04-20

### Summary of Changes
Implemented a fully automated realized dividend tracking system. The solution uses market data from yfinance to calculate dividends based on historical ownership on ex-dividend dates.

### Files Modified
- `services/market/data_fetcher.py`: Added `_calculate_realized_dividends` and `_deduce_frequency`. Updated `fetch_live`.
- `core/engine/stats_engine.py`: Updated `compute_portfolio_stats` and `build_live_table_rows`.
- `callbacks/portfolio_callbacks.py`: Added "Realized Dividends" stat card and table columns.

### Verification Results
- VHY Realized: $5.68 (Matches manual check for 7 shares @ $0.8114).
- VHY Frequency: Quarterly.
- Stability: All functions handle empty data or missing tranches gracefully.
