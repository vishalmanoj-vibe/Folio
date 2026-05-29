# Performance & Architecture Patterns — Folio

These patterns are codified to ensure the dashboard maintains its premium "Instant Load" feel and robust data handling.

### 1. Three-Interval Pattern
All pages must utilize three distinct interval types to balance UI freshness with CPU/Network efficiency:
- **Startup** (`startup-interval`, 1500ms): The only interval allowed to trigger the initial "live" data fetch. Prevents blocking the initial page paint.
- **Heartbeat** (`heartbeat-interval`, 30s): Used for lightweight UI updates (market status badges, countdowns, session progress).
- **Price/Data** (`price-interval`, 300s): The primary driver for yfinance refreshes.
  - **Constraint**: Must ALWAYS be gated by `is_market_open()` at the top of the callback.

### 2. Dependency Hygiene
- **Lazy Imports**: Libraries with large footprints (Prophet, Playwright, Scrapy) must be imported within the function scope.
  ```python
  def compute_heavy_task():
      from heavy_lib import worker  # Lazy
      worker.run()
  ```
- **Profiling**: `@profile` decorators are diagnostic only. They must never be committed to source files. If needed for long-term monitoring, use the `scripts/` directory.

### 3. Background Thread Scheduling
- **Dynamic Sleep**: Never use `time.sleep(300)` blindly in background loops if the market is closed.
- **Pattern**: Calculate the exact duration until the next trading session to save system resources.
  ```python
  from services.market.market_status import time_until_market_open
  
  def background_loop():
      while True:
          if is_market_open():
              _do_work()
              time.sleep(300)
          else:
              sleep_time = time_until_market_open()
              time.sleep(sleep_time)
  ```

### 4. Cache Key Stability
- Cache keys must exclude volatile "live" values (like current price) to ensure stable hits during a session.
- Use anchor points (first/last dates, counts) and date-stamps for daily invalidation.

### 5. Memory-Efficient Data Architecture (Phase 2)
- **Store Separation**: `portfolio-store` is for metadata and metrics only. MB-scale historical arrays MUST be excluded from dcc.Stores to prevent browser-side lag and JSON overhead.
- **Lazy Fetching**: Pages must register their own history requirements. Use `fetch_ticker_history(ticker, period)` within detail-page callbacks instead of pre-fetching all tickers on the main dashboard refresh.
- **Compact Caching**: Extract only the required `pd.Series` (Close, Dividends) from raw yfinance downloads. Discard the original `multi_full` DataFrame immediately to keep the server-side memory footprint low.
- **Relational Backing**: All historical price data is persisted in SQLite via `HistoryRepository`. Use the database for cross-session continuity instead of relying on in-memory caches.
