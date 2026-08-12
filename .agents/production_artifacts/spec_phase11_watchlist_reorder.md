# Feature Spec: Watchlist Ticker Drag & Drop Reordering

## Goal
Implement a premium, manual drag-and-drop reordering feature for the watchlist tickers. The custom order of tickers must be fully persisted to the relational SQLite database (`portfolio.db`) and survive page updates and server refreshes seamlessly.

## Stack & Technologies
- Dash (Plotly), HTML5 Drag and Drop API
- Custom Vanilla JS using Event Delegation
- SQLite for persistent storage of ordering indexes

## Key Component IDs
- `#watchlist-order-input`: A hidden text input used to pass the JSON-serialized reordered ticker list from Javascript to the Dash callback.
- `{"type": "watchlist-row", "index": TICKER}`: Assigned to each row (`html.Tr`) in the watchlist table to support structured ID access and drag handle triggers.

## Proposed Changes

### [Database] [database.py](../../data/database.py)
- In `init_db()`, add a migration to check and add the `order_index` column (default 0) to the `watchlist` table.

### [Data] [watchlist_repository.py](../../data/watchlist_repository.py)
- Modify `load_watchlist()` to select `order_index` and sort the query by `order_index ASC, added_date ASC`.
- Modify `add_ticker()` to append new tickers with an `order_index` equal to `MAX(order_index) + 1`.
- Add `update_watchlist_order(ticker_order)` to write the new order indices to the database under a transaction.

### [Components] [watchlist_layout.py](../../components/watchlist_layout.py)
- Add a hidden `html.Input(id="watchlist-order-input", ...)` field inside the layout.

### [Callbacks] [watchlist_callbacks.py](../../callbacks/watchlist_callbacks.py)
- Update `render_watchlist_table()` to render a grab handle cell `☰` on the left of each row. Set `draggable=True`, `className="draggable-row"`, and add custom `data-ticker=ticker` attribute on the `html.Tr`.
- Update `update_watchlist_store()` callback:
  - Add `Input("watchlist-order-input", "value")` to the callback triggers.
  - Parse the serialized ticker order, invoke `repo.update_watchlist_order()`, and fetch the reordered watchlist live.

### [Assets] [drag_drop.js](../../assets/drag_drop.js) (NEW)
- Implement document-level event delegation for HTML5 drag events to reorder rows locally and write back the serialized order to the Dash hidden input.

### [Assets] [view-pages.css](../../assets/view-pages.css)
- Add styling for grab cursors, dragging states, insertion markers (`.drag-over-above`, `.drag-over-below`), and grab handles.

## Verification
- Dragging a ticker row dynamically inserts insertion lines, swaps elements, and automatically saves order.
- Page reload keeps the updated order.

## Related Files
- **Skills:** [Component ID Registry](../skills/registry.md), [UI/UX Design & CSS](../skills/ui_ux.md), [Aura Design System](../skills/aura_design_system.md)
- **Reference:** [Store Contracts](../../docs/reference/store_contracts.md), [Callback Ownership](../../docs/reference/callback_ownership.md)
- **Code:** [watchlist_repository.py](../../data/watchlist_repository.py), [watchlist_callbacks.py](../../callbacks/watchlist_callbacks.py)
