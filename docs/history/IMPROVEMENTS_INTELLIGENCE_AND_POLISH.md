# Code Improvements — Technical Intelligence & UI Polish

> Back to [IMPROVEMENTS.md](IMPROVEMENTS.md)

This document contains the detailed log of code improvements implemented for Folio's technical indicator engines, AI optimizations, layout stabilization, and background workers (Items 21–34).

---

### 21. **Technical Analysis Engine (Pure Pandas)** ✅
**Files Modified:** `services/technical_indicators.py` (New), `callbacks/intelligence_callbacks.py`

**What Was Added:**
- Pure-pandas implementation of common technical indicators (RSI, MACD, Bollinger Bands).
- **Wilder's RSI**: Uses `ewm(com=period-1)` to match industry-standard calculations.
- **MACD**: Standard (12, 26, 9) signal line crossover logic.
- **Bollinger Bands**: 20-day SMA +/- 2 standard deviations.
- **Signal Classification**: Automated labeling (Oversold, Bullish, etc.) for high-density UI tables.

**Benefits:**
- **Zero Dependencies**: No need for `pandas_ta` or `talib`, keeping the environment lean.
- **High Performance**: Vectorized pandas operations ensure fast calculation for 50+ tickers.
- **Unified Logic**: One service provides indicators for both the Insights page and AI Assistant context.

---

### 22. **OHLC Data & Candlestick Support** ✅
**Files Modified:** `services/market/data_fetcher.py`, `pages/positions.py`

**What Was Added:**
- Refactored market data extraction to pull **Open, High, Low, and Close** columns.
- Support for `go.Candlestick` charts in the Positions deep-dive.
- **Intraday Fallback**: Automatic reversion to Line charts when OHLC data is missing (common for "1d" period).

**Benefits:**
- Professional-grade market visualization.
- Better visibility into intraday price action and volatility.

---

### 23. **Multi-Page Period Synchronization** ✅
**Files Modified:** `app.py`

**What Was Added:**
- Global synchronization logic that listens to all page-specific period stores (`positions-period-store`, `watchlist-period-store`, etc.).
- The master `portfolio-store` refresh now fetches the **maximum requested period** across all pages.

**Benefits:**
- Seamless navigation: switching from the Holdings (1y) to Positions (max) no longer requires a waiting for a new network fetch.
- Reduced API overhead by consolidating disparate time-period requests into a single bulk fetch.

---

### 24. **AI Research Signal Injection** ✅
**Files Modified:** `services/research_service.py`

**What Was Added:**
- Automatically injects live technical status (RSI/MACD/BB) into the context prompt for Gemini.
- The AI now "sees" if a stock is oversold or has a bullish MACD crossover when evaluating a prospective buy.

**Benefits:**
- Higher fidelity AI reasoning.
- Contextualizing technical math with qualitative portfolio goals.

---

### 25. **AI Engine Optimization & Cost Management** ✅
**Files Modified:** `services/ai_engine.py`

**What Was Added:**
- **Deterministic Caching**: Refactored the `cache_key` generation to use a stable subset of signals. By hashing only the signal (BUY/SELL/HOLD) and the rounded score (1 decimal place) while ignoring highly volatile live price ticks, the 24-hour cache hit rate is significantly improved.
- **SDK Compatibility Fix**: Removed the unsupported `request_options` parameter from the `google.genai` SDK call, resolving a hidden `TypeError` that was causing the "AI analysis unavailable" fallback.

**Benefits:**
- **Zero Redundant Costs**: Minimizes API calls by preventing minor price fluctuations from busting the cache.
- **Improved Reliability**: Restores the Assistant Insight functionality for all tickers.

---

### 26. **AI Insight Layout Isolation** ✅
**Files Modified:** `pages/positions.py`, `components/watchlist_layout.py`, `callbacks/positions_callbacks.py`, `callbacks/watchlist_callbacks.py`

**What Was Added:**
- **Container Separation**: Introduced `ai-insight-container` on both the Positions and Watchlist pages.
- **Grid Stability**: Isolated the AI text block from the primary metrics CSS Grid. This prevents the large text content from forcing the metric cards to shrink to their minimum width (`auto-fit` compression).
- **Typography Standards**: Upgraded AI explanation text from tiny 9px "sub-text" to standard readable 13px font with a 1.5 line height.
- **Themed Metrics**: Styled technical scores and labels using the primary accent color (`var(--cyan)` / Teal) for visual consistency.

**Benefits:**
- **Layout Integrity**: Metric cards maintain their size regardless of AI content length.
- **Readability**: AI analysis is now easy to read at a glance.

---

### 27. **Watchlist Chart Axis Scaling** ✅
**Files Modified:** `callbacks/watchlist_callbacks.py`

**What Was Added:**
- **Dynamic Y-Axis Range**: Calculated the minimum and maximum price for the selected period.
- **Zoomed View**: Configured the Y-axis range to `[min * 0.98, max * 1.02]`.

**Benefits:**
- **Better Data Density**: Eliminates the massive empty gap at the bottom of the chart caused by the default "start at $0" behavior (from `fill="tozeroy"`).
- **Price Precision**: Small price movements are now clearly visible on high-priced assets.

---

### 28. **Dividend Consolidation & UI Layout Standardization** ✅
**Files Modified:** `pages/positions.py`, `services/market/dividend_service.py`, `assets/layout.css`, `components/ui_helpers.py`

**What Was Added:**
- **Consolidated Positions View**: Merged the standalone Dividend Dashboard into the Positions page. Redundant top-level summary strips and standalone pages were eliminated to reduce "dashboard dumping".
- **Centralized Dividend Service**: Created `dividend_service.py` to handle all income math, realized distributions, and trend projections.
- **UI Grid Standardization**: Established a global `16px 24px` padding standard for all page headers and sections.
- **Dynamic Container Pattern**: Refactored Positions and Watchlist pages to use dynamic containers that stay hidden until a ticker is selected, preventing empty headers and "Day 1" layout glitches.

**Benefits:**
- **Reduced Complexity**: Fewer pages and cleaner navigation.
- **Visual Consistency**: Every page now feels part of a single, unified design system.
- **Professional Empty States**: No more empty graphs or "No Data" strings on initial page load.

---

### 29. **Portfolio Suggestion Integration** ✅
**Files Modified:** `callbacks/portfolio_callbacks.py`

**What Was Added:**
- **Signal Badge Column**: Injected a "Suggestion" column into the main Holdings Overview table.
- **Hybrid Data Flow**: Consumers signals from the `signals-store` (populated on the Positions page) to display BUY/SELL/HOLD status for each holding.
- **Performance Optimization**: Uses `State` for signal data to prevent table re-renders when the store updates in the background.

**Benefits:**
- **Immediate Actionability**: See market signals directly alongside current P&L.
- **Unified Logic**: Reuses the same strategy engine scoring across both deep-dive and Holdings pages.

---

### 30. **Deep Dive Visualization & Theming** ✅
**Files Modified:** `pages/analytics.py`, `components/charts/treemap.py`

**What Was Added:**
- **Surface Harmonization**: Eliminated grey canvas artifacts by setting Plotly background transparency to blend with CSS `--surface` tokens.
- **Theme-Aware Text**: Mapped chart labels to `--t-pri` variables for contrast in both light and dark modes.
- **Clean Layouts**: Stripped default Plotly templates to remove redundant grid lines and ensure a modern, premium aesthetic.

**Benefits:**
- **Professional UI**: Charts look like native application components rather than embedded "iframe" style plots.
- **Readability**: High contrast text ensures data is legible regardless of the active theme.

---

### 31. **Architecture Compliance Audit** ✅
**Files Modified:** Project-wide

**What Was Added:**
- **Logging Standardization**: Replaced all remaining `print()` statements in `services/` and `core/` with `logger.debug()` for better production observability.
- **Callback Verification**: Confirmed `prevent_initial_call=True` for all page-specific callbacks to eliminate race conditions during navigation.
- **Aura Design Compliance**: Verified that all new UI blocks use standard `section()` helpers and CSS variables.

**Benefits:**
- **System Stability**: Fewer navigation crashes and silent errors.
- **Operational Excellence**: Clean logs and consistent design patterns across the entire codebase.

---

### 32. **Aesthetic Excellence & Chart Standardization** ✅
**Files Modified:** `components/charts/helpers.py`, `assets/layout.css`

**What Was Added:**
- Unified all charts via `apply_standard_layout()` for consistent typography and hover UX.
- Implemented glassmorphism nav bar and 200ms theme transitions.
- Added real-time animated market status heartbeat to the header.

**Benefits:**
- "Linear-grade" UI polish with high-performance frosted glass effects.
- Consistent typography (Inter 10px) across all 15+ visualizations.

---

### 33. **Performance Baseline & Multi-Tier Intervals** ✅
**Files Modified:** `app.py`, `config/settings.py`, `core/cache.py`

**What Was Added:**
- Established memory and CPU baselines for all core rendering and fetch callbacks.
- Replaced the unconditional 5-minute global refresh with a dual-interval strategy: 30s UI heartbeat and 300s gated data refresh.
- Lazy Loading Prophet: Implemented a lazy loading architecture for Facebook Prophet, drastically reducing baseline memory consumption.

**Benefits:**
- Reduced idle CPU cycles by gating network fetches to market hours.
- Significant reduction in baseline RAM footprint.

---

### 34. **Enterprise-Grade Memory Hygiene & Distributed Architecture** ✅
**Files Modified:** `launcher.py`, `worker.py`, `services/market/holdings_fetcher.py`, `data/repository.py`, `components/charts/price_history.py`

**What Was Added:**
- **Dual-Process Resilience**: Implemented a `launcher.py` process manager that separates the Dash UI from the data-heavy background worker.
- **Startup Task Decentralization**: Offloaded intensive historical data hydration (e.g., Watchlist histories) from the web startup sequence to the background worker.
- **Distributed ETF Scraping**: Offloaded the *execution* of Playwright-based ETF holdings scrapers to the background worker, preventing browser-driven RAM spikes in the web process.
- **Smart Depth Awareness**: Refactored the `is_stale` logic to handle young tickers (listed < 220 days) by tracking the history period in metadata.
- **Stable Hover Templates**: Standardized Plotly hovertemplates to use doubled braces (`%{{y}}`) to prevent runtime f-string rendering crashes.
- **Staleness Gating**: Enforced a strict 24-hour staleness threshold for historical price updates.

**Benefits:**
- **System Stability**: The web process remains lightweight (~300MB) with no memory leaks.
- **Bandwidth Savings**: Prevents redundant "max" price lookups.
- **Robust UI**: No Plotly name-resolution errors during theme transitions.
