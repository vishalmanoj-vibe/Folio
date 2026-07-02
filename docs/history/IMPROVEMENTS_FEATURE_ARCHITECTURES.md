# Code Improvements — Feature Architectures & Orchestrations

> Back to [IMPROVEMENTS.md](IMPROVEMENTS.md)

This document contains the detailed log of code improvements implemented for Folio's core page features, UI layout engines, and modular stylesheets (Items 12–20).

---

### 12. **Insights Dashboard & Risk Engine** ✅
**Files Modified:** `pages/intelligence.py`, `services/intelligence_service.py`

**What Was Added:**
- Unified risk engine calculating Annualized Volatility, Sharpe Ratio, and Max Drawdown.
- Treemap allocation charts (Sector/Geography) with modal drill-downs for ticker exposure.
- Hierarchical risk analysis logic with automated "Others" category aggregation.
- Rule-based "Smart Alerts" system for portfolio concentration and risk monitoring.

---

### 13. **Portfolio Forecasting (Prophet Integration)** ✅
**Files Modified:** `services/prediction_service.py`, `data/cache/`

**What Was Added:**
- Facebook Prophet integration for forward-looking portfolio projections.
- Automated confidence interval (80%) generation.
- Persistent disk-caching (`predictions.json`) to ensure UI responsiveness.
- Seamless baseline normalization to align historical curves with future forecasts.

---

### 14. **Deep Dive & Correlation Matrix** ✅
**Files Modified:** `pages/analytics.py`, `components/charts/correlation.py`

**What Was Added:**
- Tabbed interface for high-density metrics (Allocation, Performance, Income).
- Normalized Price History chart for multi-ticker comparison.
- Dynamic Correlation Matrix heatmap for diversification analysis.
- Multi-period filtering (1mo to max) integrated into deep-dive views.

---

### 15. **Realized Dividend Tracking** ✅
**Files Modified:** `services/market/data_fetcher.py`

**What Was Added:**
- Historical ex-dividend date matching against user tranches.
- Programmatic calculation of dividend income based on exact holding windows.
- Unified dividend stats integrated into the stat card layer.

---

### 16. **Technical Optimizations & Theme Stability** ✅
**Files Modified:** `callbacks/intelligence_callbacks.py`, `services/intelligence_service.py`, `pages/intelligence.py`

**What Was Added:**
- **Risk Metrics Optimization**: Pre-computation of returns once per cycle, eliminating redundant processing in prediction mode.
- **Metadata Robustness**: Improved safety checks for `funds_data` with tiered fallbacks (Category search -> Region inference).
- **Theme Awareness Fixes**: Replaced Python-side hex constants with CSS variables (`var(--t-pri)`, etc.) in layout code to ensure consistent theme switching without page reloads.

---

### 17. **Modular CSS Architecture** ✅
**Files Modified:** `assets/`

**What Was Added:**
- Migrated from monolithic `styles.css` to a modular system.
- Alphabetical loading priority: `base.css` (variables) -> `components.css` -> `vendor.css` (overrides).
- High-specificity CSS selectors for overriding Radix-based Dash components.

---

### 18. **Single Refresh Owner Pattern** ✅
**Files Modified:** `app.py`, `callbacks/transaction_callbacks.py`

**What Was Added:**
- Consolidated all store update logic into two dedicated "Master" callbacks in `launcher.py` and `app.py`.
- `update_txn_store`: Single source of truth for transaction data.
- `update_portfolio_store`: Exclusive caller of `fetch_live()`, preventing redundant network calls.
- Removed multiple overlapping refresh callbacks to stabilize the application event loop.

**Benefits:**
- Eliminates race conditions and "chain reaction" refreshes.
- Significant reduction in redundant network I/O.
- Predictable and reliable state management.

---

### 19. **Parallel Market Fetching & Metadata Caching** ✅
**Files Modified:** `services/market/data_fetcher.py`

**What Was Added:**
- Refactored `fetch_live()` to use `ThreadPoolExecutor` (10 workers) for parallelizing I/O-bound metadata requests.
- Implemented an in-memory TTL cache for Yahoo Finance metadata (long names, dividend frequencies).
- Collapsed sequential network wait times from `N * Latency` to `max(Latency)`.

**Benefits:**
- Drastically faster dashboard refreshes, especially for portfolios with many holdings.
- Reduced API overhead via smart metadata caching.

---

### 20. **Data Repository Abstraction Layer** ✅
**Files Modified:** `data/repository.py` (New), `app.py`

**What Was Added:**
- Introduced `PortfolioRepository` class to abstract data access from storage format.
- Methods: `load_transactions()`, `save_transactions()`, `append_transaction()`.
- Decoupled presentation logic from persistence via `PortfolioRepository`.
- Fully migrated from legacy CSV storage to production-ready SQLite with WAL support.

**Benefits:**
- Improved architectural modularity.
