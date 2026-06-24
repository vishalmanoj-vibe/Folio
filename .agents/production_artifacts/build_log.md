# Build Log: Holdings and Transaction Table Deep-linking to Positions

This build implements Option A: query parameter-based deep-linking (`/positions?ticker=XYZ`) to navigate from the holdings table (Overview page) and the transaction history table directly to the Positions page with the corresponding ticker card selected.

## Changed Files
- **[callbacks/portfolio_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/portfolio_callbacks.py)** [MODIFY]: Updated the holdings table ticker link to point to `/positions?ticker={ticker}`.
- **[components/ui_helpers.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/ui_helpers.py)** [MODIFY]: Updated the transaction history table ticker link to point to `/positions?ticker={ticker}`.
- **[callbacks/positions_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/positions_callbacks.py)** [MODIFY]: Refactored `select_ticker` callback to listen to `url.search` and `url.pathname`. Enforced page pathname gating to `/positions` to prevent off-page background execution. Implemented query parameter extraction, validation against existing holdings, and state-synchronization guards to ensure background refreshes do not overwrite manual card selections.
- **[scratch/tests/test_positions_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scratch/tests/test_positions_callbacks.py)** [NEW]: Created a comprehensive unit test suite covering off-page gating, card selection, ghost click filtering, URL deep-linking, invalid ticker fallback, and background refresh preservation.

## Verifications Passed
- Automated test suite executed via `scratch/run_tests.sh`: all **191 unit tests passed successfully**!
