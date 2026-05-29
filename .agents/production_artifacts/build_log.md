# Build Log: Watchlist Drag-and-Drop Reordering

This build successfully introduces manual drag-and-drop reordering for the market watchlist tickers.

## Changed Files
- **[database.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/data/database.py)**: Added `order_index` to `watchlist` table creation and added Migration 16.
- **[watchlist_repository.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/data/watchlist_repository.py)**: Added `order_index` sorting inside `load_watchlist()`, dynamically computed next index on `add_ticker()`, and implemented transactional `update_watchlist_order()`.
- **[watchlist_layout.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/watchlist_layout.py)**: Injected hidden input element `#watchlist-order-input`.
- **[watchlist_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/watchlist_callbacks.py)**: Enabled row `draggable="true"`, rendered grab handle column `☰` with cursor helpers, and registered reorder callback handler within `update_watchlist_store()`.
- **[view-pages.css](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/view-pages.css)**: Appended styles for grabbing cursor states, transparent active dragging row states, and high-contrast insertion line highlights.

## New Files
- **[drag_drop.js](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/drag_drop.js)**: Created client-side HTML5 drag-and-drop event-delegated engine that hooks row drops to Dash state updates.

## Component IDs Registered
- `#watchlist-order-input`
- `{"type": "watchlist-row", "index": TICKER}`

## Verifications Passed
- Python 3 compile syntax check: Passed.
