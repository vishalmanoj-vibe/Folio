# Feature Spec: Landing Page Memory & Performance Optimizations

## Goal
Resolve the memory leak and performance thrashing that causes the landing page RAM usage to balloon to 1.2GB. This is achieved by:
1. Decoupling the heavy `pnl_history_chart` callback from the high-frequency 2s `task-poll-interval` trigger on the backend.
2. Optimizing the frontend MutationObservers in `sync_hover.js` and `countup.js` to eliminate redundant listener re-bindings and DOM traversals.

## Stack & Technologies
- Dash/Plotly Python Callback system
- SQLite (benchmark cache read status)
- Vanilla HTML5 JavaScript MutationObservers (restricted and debounced)

## Key Component IDs
- `pnl-history-chart`: Rebuilds only on parameters/data updates.
- `benchmark-pending-store`: Used to poll for benchmark task status.
- `task-poll-interval`: Drives the lightweight status checker when enqueued.

## Proposed Changes

### [MODIFY] [chart_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/chart_callbacks.py)
- **Remove** `Input("task-poll-interval", "n_intervals")` from `pnl_history_chart`.
- **Add** a lightweight status polling callback `poll_benchmark_status` that runs only when `benchmark-pending-store` is active, checks SQLite benchmarks database, and sets the store to `None` when completed.
- **Add** `Input("benchmark-pending-store", "data")` (as an Input or State) to `pnl_history_chart` to trigger a final redraw when benchmarks complete.

### [MODIFY] [sync_hover.js](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/sync_hover.js)
- Filter nodes added during mutations to ensure they contain `.js-plotly-plot` before triggering hover synchronisation.
- Add a 100ms debounce timer to prevent setupSync from running repeatedly during rendering updates.

### [MODIFY] [countup.js](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/countup.js)
- Observe `childList` additions only and disable `characterData` tracking to avoid intercepting intermediate animation frames.

## Fallback States
- If the lightweight status checker fails, the benchmark task will time out and task-poll-interval will disable automatically.
- If MutationObservers fail, hover syncing and countup animations fallback gracefully without affecting dashboard functionality.
