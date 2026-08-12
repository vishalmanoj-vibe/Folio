# Technical Spec — Page Load Stabilization for Newly Added Tickers

Stabilize the Positions and Watchlist pages by preventing `UnboundLocalError` crashes when a new ticker has no cached historical price data.

---

## Modified/New Files List

- `callbacks/positions_callbacks.py` (Modify)
- `callbacks/watchlist_callbacks.py` (Modify)

---

## Component IDs & Data Strategy
- No new Dash component IDs are introduced.
- Consumes existing `HistoryRepository` close series.
- Ensures robust fallback: if history is missing, the callbacks return `None` (empty child) for technical indicator badges rather than raising an exception.

---

## Resolved Pain Points & Fallback States
- **Page Crash on Empty Cache**: If a newly added ticker has no cached history in SQLite, the `UnboundLocalError` crash causes the callback to fail, leaving the front-end stuck. Resolving this allows page metrics and charts to paint immediately with default empty states (standard skeletons, empty Plotly charts, and None for technical indicators).
- **Startup Sync Isolation**: Newly added tickers are registered in SQLite immediately. If the user starts the server using `launcher.py` as documented in `README.md`, a background queue task is generated and processed by the worker to fetch the required historical data, resolving the empty cache state.

---

## Proposed Changes

### Positions Page Callback
In [positions_callbacks.py](../../callbacks/positions_callbacks.py):
Initialize `tech_signals = None` before fetching and checking the close series:
```python
        # Generate Tech Signals (Memory Optimized)
        from data.repository import HistoryRepository

        tech_signals = None
        history_s = HistoryRepository().load_close_series(
            ticker, from_date=(pd.Timestamp.now() - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
        )
        if not history_s.empty:
            tech_signals = tech_signal_badges(ticker, history_s)
```

---

### Watchlist Page Callback
In [watchlist_callbacks.py](../../callbacks/watchlist_callbacks.py):
Initialize `tech_signals = None` before fetching and checking the close series:
```python
        # Generate Tech Signals (Memory Optimized)
        from data.repository import HistoryRepository

        tech_signals = None
        history_s = HistoryRepository().load_close_series(
            selected_ticker,
            from_date=(pd.Timestamp.now() - pd.DateOffset(years=1)).strftime("%Y-%m-%d"),
        )
        if not history_s.empty:
            tech_signals = tech_signal_badges(selected_ticker, history_s)
```

---

## Verification Plan

### Automated Tests
- Run `bash scratch/run_tests.sh` to verify no regressions in the mock-isolated unit tests.

### Manual Verification
- Start the app and worker processes using the launcher: `python launcher.py`.
- Navigate to the Positions and Watchlist pages and verify that they load successfully.

## Related Files
- **Skills:** [Component ID Registry](../skills/registry.md), [Data Fetching & Scrapers](../skills/data_fetching.md)
- **Reference:** [Known Issues](../../docs/reference/known_issues.md)
- **Code:** [positions_callbacks.py](../../callbacks/positions_callbacks.py), [watchlist_callbacks.py](../../callbacks/watchlist_callbacks.py)
