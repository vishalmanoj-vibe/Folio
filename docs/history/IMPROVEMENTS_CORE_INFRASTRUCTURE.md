# Code Improvements — Core Infrastructure & Resilience

> Back to [IMPROVEMENTS.md](IMPROVEMENTS.md)

This document contains the detailed log of code improvements implemented for Folio's core infrastructure, input validations, configurations, logging, and database layers (Items 1–11).

---

### 1. **Input Validation Pipeline** ✅
**Files Modified:** `core/validators.py`

**What Was Added:**
- Centralized `validate_transaction()` logic to validate structure before persistence.
- Validates required keys, numeric types, positive values, and YYYY-MM-DD date formats.
- Used by the Repository layer to ensure database integrity.
- Returns tuple `(is_valid: bool, error_message: str)` for clear error reporting.

**Benefits:**
- Prevents data corruption from malformed transactions
- Clear error messages for debugging
- Graceful degradation (partial portfolio if some transactions invalid)

**Example:**
```python
is_valid, error = validate_transaction(txn)
if not is_valid:
    logger.warning(f"Invalid transaction: {error}")
```

---

### 2. **API Failure & Retry Logic** ✅
**Files Modified:** `services/market/data_fetcher.py`, `config/settings.py`

**What Was Added:**
- New `_download_with_retry()` helper function with exponential backoff
- Configured via environment variables: `API_MAX_RETRIES`, `API_RETRY_BACKOFF_BASE`
- Retries transient failures (network errors, rate limits)
- Falls back to cost basis gracefully on persistent failures
- Detailed debug logging for each attempt

**Configuration Options:**
```
API_MAX_RETRIES=3              # Number of retry attempts (default 3)
API_RETRY_BACKOFF_BASE=2.0     # Exponential backoff multiplier (default 2.0)
```

**Benefits:**
- More resilient to temporary network issues
- Reduces unnecessary API quota consumption
- Better debugging visibility
- Configurable retry behavior for different environments

---

### 3. **Configuration Management with Environment Variables** ✅
**Files Modified:** `config/settings.py`, `core/cache.py`, `services/alert_service.py`

**What Was Added:**
- All hardcoded values now support environment variable overrides
- Backward compatible (uses sensible defaults if no env var set)

**Environment Variables:**
```bash
DB_PATH                                # SQLite database path (default data/portfolio.db)
REFRESH_INTERVAL_MS                    # Screen refresh interval (default 300000ms / 5m)
MARKET_TIMEZONE                        # Market timezone (default Australia/Sydney)
API_MAX_RETRIES                        # API retry attempts (default 3)
API_RETRY_BACKOFF_BASE                 # Retry backoff base (default 2.0)
TECHNICALS_CACHE_TTL                   # RSI/MACD cache (default 24h)
DIVIDENDS_CACHE_TTL                    # Dividend cache (default 7d)
ALERT_INDIVIDUAL_DRAWDOWN_PCT          # Individual alert threshold (default -20%)
ALERT_PORTFOLIO_DRAWDOWN_PCT           # Portfolio alert threshold (default -15%)
LOG_LEVEL                              # Logging level (default INFO)
GEMINI_API_KEY                         # Required for Assistant & Research
```

**Benefits:**
- Deploy same code to different markets/environments
- Easy testing with different configurations
- No code changes needed for deployment variations
- Example file `.env.example` provided

---

### 4. **Market Hours Configuration** ✅
**Files Modified:** `services/market/market_status.py`, `config/settings.py`

**What Was Added:**
- Market check now uses configurable timezone, weekdays, and hours from config
- Replaces hardcoded Australia/Sydney 10:00-16:00 hours
- Can be extended to other markets without code changes

**Configuration Options:**
```
MARKET_TIMEZONE                # Timezone string (default "Australia/Sydney")
# Hours and weekdays currently hardcoded but easily configurable
```

**Example Usage:**
```python
# For US markets:
MARKET_TIMEZONE=America/New_York
# Update MARKET_HOURS in config.py to (9.5, 16)  # 09:30-16:00
```

**Benefits:**
- Supports multiple markets
- Less fragile than hardcoded timezones
- Can be extended to support configurable hours

---

### 5. **Dividend Refetching Optimization** ✅
**Files Modified:** `services/market/dividend_service.py`

**What Was Added:**
- Refactored to use centralized `DIVIDENDS_CACHE_TTL` (7-day persistent cache).
- Consolidated distribution logic from ex-dividend date matching to trend projections.

**Current State:**
- Dividends fetched per ticker (unavoidable limitation of yfinance bulk API)
- Added caching via CACHE_TTL_SECONDS environment variable
- Per-ticker fetch is wrapped in try/except with proper fallback

**Future Optimization Opportunity:**
- yfinance bulk downloads don't include Dividends column
- Could cache per-ticker dividend history separately to reduce API calls
- Currently acceptable for typical portfolios (5-10 holdings)

**Benefits:**
- Configurable cache duration
- Reduces redundant API calls for same period

---

### 6. **Logging Configuration** ✅
**Files Modified:** `app.py`, `config/logging.py` (new)

**What Was Added:**
- Centralized logging configuration in new `logging_config.py`
- Separate console and file handlers
- Suppresses noisy third-party loggers (yfinance, urllib3)
- Configurable via environment variables

**Configuration Options:**
```
LOG_LEVEL=INFO              # Console log level (default INFO)
LOG_FILE=portfolio.log      # Log file path (default portfolio.log)
LOG_FILE_ENABLED=true       # Enable file logging (default true)
```

**Features:**
```
- Formatted timestamps in logs
- Separate formatting for console (compact) vs file (detailed)
- Automatic file rotation capability (if needed)
- Suppresses DeprecationWarning noise
```

**Benefits:**
- Production-grade logging setup
- Easy debugging with file logs
- Configurable verbosity per environment
- Better visibility into API calls, errors, and state changes

**Example Log Output:**
```
[INFO    ] services.market_data    : Fetching ['VHY.AX', 'VAS.AX']  period=3mo
[DEBUG   ] services.market_data    : Cache hit for period=3mo
[INFO    ] services.alert_service  : Portfolio down -18.50% overall
```

---

### 7. **Alert Customization** ✅
**Files Modified:** `services/alert_service.py`, `config/settings.py`

**What Was Added:**
- Alert service now accepts optional `thresholds` parameter
- Defaults to `ALERT_THRESHOLDS` from config
- Individual and portfolio thresholds independently configurable

**Configuration Options:**
```
ALERT_INDIVIDUAL_DRAWDOWN_PCT=-20.0    # Per-holding alert (default -20%)
ALERT_PORTFOLIO_DRAWDOWN_PCT=-15.0     # Total portfolio alert (default -15%)
```

**Example:**
```python
# Override defaults for strict monitoring
alerts = check_alerts(holdings, thresholds={
    "individual_drawdown": -10.0,  # Alert at -10% instead of -20%
    "portfolio_drawdown": -5.0,    # Alert at -5% instead of -15%
})
```

**Benefits:**
- Different alert thresholds for different strategies
- Easy A/B testing of alert rules
- No code changes needed for threshold adjustments

---

### 8. **Relational Transaction Integrity (SQLite)** ✅
**Files Modified:** `data/database.py`, `data/repository.py`

**What Was Added:**
- Migrated from CSV to SQLite for all core persistence.
- **WAL Mode**: Enabled Write-Ahead Logging for safe concurrent access between UI and background fetchers.
- **Atomic Transactions**: Full rollback support on database write failures.
- **Implicit Relationships**: Tickers in transactions are normalized and linked to the `assets` metadata table.

**Benefits:**
- Eliminates CSV corruption and file-locking issues.
- Drastically faster data retrieval for large histories.
- Robust state management across multiple pages and background threads.

---

### 9. **Modular Architecture & Testing Framework** ⚠️
**Status:** Refactoring in Progress

**Recent Changes:**
- Unit tests for legacy CSV logic have been decommissioned.
- **New Target**: Comprehensive testing for `PortfolioRepository`, `StrategyEngine`, and `PortfolioEngine`.
- **Manual Verification**: Established standard walkthroughs for AI and UI components (see `TESTING.md`).

**Planned:**
- Integration tests for the Single Refresh Owner loop.
- Mocked API testing for `data_fetcher` resiliency.

---

### 10. **Documentation Updates** ✅
**Files Created/Modified:**
- `.env.example` - Environment variable template
- `TESTING.md` - Testing guide and walkthrough
- `IMPROVEMENTS.md` - Index file

**What Was Added:**
- `.env.example` - Copy and customize for your environment
- `TESTING.md` - How to run tests, where to find test code
- Updated docstrings in modified functions

---

### 11. **Project Refactoring & Cohesion** ✅
**Files Modified:** Project-wide (20+ files)
 
**What Was Added:**
- Standardized naming convention across all layers (Callbacks, Components, Services)
- Renamed legacy files for better discovery (e.g., `core_callbacks.py` -> `portfolio_callbacks.py`)
- Unified service naming (e.g., `alerts.py` -> `alert_service.py`)
- Standardized directory structure for market services (`services/market/`)
- Comprehensive docstring audit and import cleanup
 
**Benefits:**
- Drastically improved developer onboarding
- Clearer mental model of where logic lives
- Prevents import name collisions
- Consistent with modern Python repository patterns
