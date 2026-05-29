# Feature Spec: Automatic Dividend Tracking

## Goal
Automatically calculate and display realized dividends and distribution frequencies for all portfolio holdings using historical market data and transaction dates.

## Key Logic
- **Realized Dividends**: Calculated by `Dividend Amount * Shares Held on Ex-Date`.
- **Frequency**: Deduced from historical payment intervals (Quarterly, etc.).
- **Data Source**: yfinance `Dividends` series.

## Proposed Changes

### [Service] [data_fetcher.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/services/market/data_fetcher.py)
- Implement `_calculate_realized_dividends` and `_deduce_frequency`.
- Enrich holdings in `fetch_live` with:
    - `realized_div`: Total cash received to date.
    - `div_frequency`: Payment schedule (Quarterly, etc.).
    - `last_div_amount`: Amount of the most recent distribution.

### [Core] [engine/stats_engine.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/core/engine/stats_engine.py)
- Aggregate `total_realized_div` in `compute_portfolio_stats`.
- Include dividend metadata in `build_live_table_rows`.

### [Callbacks] [portfolio_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/portfolio_callbacks.py)
- Update "Live positions" table with "Realized Div" and "Freq" columns.
- Update stat cards to show total realized dividends.

## Verification
- VHY should show $5.68 realized for the 7 shares held on April 1, 2026.
- Frequency for VHY should be "Quarterly".
