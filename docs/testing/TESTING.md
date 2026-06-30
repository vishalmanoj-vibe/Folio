# High-Performance Isolated Testing Guide

Folio includes a world-class, automated test and code quality framework. All unit tests run in **completely offline, sandbox-isolated environments** to ensure fast, deterministic, and network-free execution.

---

## 🏗️ Core Testing Principles

1. **Zero-Network Isolation**: No test is allowed to trigger real Yahoo Finance downloads, DuckDuckGo searches, or Google Gemini API requests. Everything is strictly mocked.
2. **Database Cleanliness**: Tests interact with isolated, fresh in-memory or temporary SQLite databases. The main `portfolio.db` is never read or written to during testing.
3. **Modern Type Safety**: All files are strictly typed. We use modern, non-deprecated Python 3.12+ type hints (e.g. standard `list` and `dict` rather than `typing.List` and `typing.Dict`).
4. **Strict Style Compliance**: Every test suite and application file must pass `ruff` format and lint checks, as well as strict `mypy` static analysis.

---

## 📁 Test Architecture & Layout

All unit tests are organized inside the `scratch/tests/` directory to prevent codebase clutter. There are **28 test suites** in total, evaluating **197 mock-isolated test cases**:

```text
scratch/
├── run_tests.sh              # Unified Test Runner
└── tests/
    ├── test_ai_engine.py             # Analyst overlay, verdict mapping, client mocks
    ├── test_alert_callbacks.py      # Alert notifications, thresholds, UI banners
    ├── test_chart_components.py     # go.Figure builders (PnL history, allocations, etc.)
    ├── test_data_fetcher.py         # Bulk Yahoo Finance downloads and caching logic
    ├── test_dividend_service.py     # Tranche matching, ex-date eligibility, yield calculations
    ├── test_intelligence_service.py # Portfolio risk math (Sharpe, Volatility, Drawdowns)
    ├── test_layouts.py              # Header and dynamic page structure sanity checks
    ├── test_market_status.py        # ASX session calendars and Sydney timezone checks
    ├── test_portfolio_callbacks.py  # Holdings table rendering, sorting, and stats
    ├── test_portfolio_engine.py     # Cost-basis tranches and P&L aggregations
    ├── test_positions_callbacks.py  # Card selections, detail metrics, chart container states
    ├── test_prediction_service.py   # FB Prophet caching and forecasting validation
    ├── test_report_service.py       # Matplotlib report generation and PDF compilation
    ├── test_repository.py           # SQLite WAL connections, transactions CRUD
    ├── test_research.py             # Gemini context builder, log pruning, smart searches
    ├── test_session_cache.py        # Intraday 5-min snapshot SQLite cache operations
    ├── test_settings_callbacks.py   # Settings page, profile selection, weight previews
    ├── test_setup_callbacks.py      # Onboarding steps, task polling, redirect guards
    ├── test_signals_callbacks.py    # Manual signal triggers and task status polling
    ├── test_strategy_engine.py      # Weighted BUY/SELL/HOLD scores, hysteresis
    ├── test_technical_indicators.py # Pure pandas RSI, MACD, and Bollinger Bands
    ├── test_transaction_callbacks.py# Add, edit, validation of ledger transactions
    ├── test_ui_callbacks.py         # Theme toggles, compact mode, sorting states
    ├── test_ui_helpers.py           # Color interpolations, stat card, section wrappers
    ├── test_watchlist_callbacks.py  # Watchlist table, notes save, drag-and-drop ordering
    └── test_worker_tasks.py         # Background worker queue and task polling
```

### Coverage Overview & Deep-Dives

Our 28 primary test suites cover the core business math, data layers, and visual rendering paths:

| Test Group | Test Suites | Focus Area |
| :--- | :--- | :--- |
| **Market Data** | `test_data_fetcher.py`, `test_market_status.py`, `test_session_cache.py` | Validates trading calendars, Sydney timezone logic, yfinance downloads, and intraday cooldown caches. |
| **Core Calculations** | `test_portfolio_engine.py`, `test_dividend_service.py` | Verifies P&L math, cost basis, transaction tranches, and ex-date dividend eligibility. |
| **Technical & Strategy** | `test_technical_indicators.py`, `test_strategy_engine.py` | Validates RSI, MACD, Bollinger Bands formulas (pure pandas) and rule-based BUY/SELL scoring. |
| **AI Analyst & Assistant** | `test_ai_engine.py`, `test_research.py`, `test_report_service.py` | Mocks Gemini completions, context generation, smart news searches, conversation memory, and Matplotlib PDF reports. |
| **Database & Repos** | `test_repository.py` | Evaluates WAL mode SQLite transactions, CRUD operations, and watchlist persistence. |
| **UI Rendering & Callbacks** | `test_ui_callbacks.py`, `test_portfolio_callbacks.py`, `test_positions_callbacks.py`, `test_watchlist_callbacks.py` | Tests Dash state reactivity, page-aware callback gating (prioritized rendering), and drag-and-drop order updates. |

---

## 🚀 Running the Automated Test Suite

### 1. The Unified Test Runner
We provide a single, robust bash script that automatically manages virtual environment discovery, pytest execution, and coverage reporting:

```bash
# Run all unit tests and generate coverage metrics
./scratch/run_tests.sh
```

### 2. Inspecting Code Coverage
Our test runner generates an interactive HTML coverage map under `htmlcov/`. To inspect exactly which lines of code are covered by the automated suite, open the report in your web browser:

```bash
# Open the interactive HTML coverage map
open htmlcov/index.html
```

---

## 🛡️ Pre-Commit Hook Integration

To guarantee that no broken, unformatted, or untyped code is ever committed to the repository, Folio uses a Git pre-commit workflow (`.pre-commit-config.yaml`). 

Before any code is successfully committed, the following hooks are automatically executed:
1. **Ruff Format**: Enforces standard PEP-8 style formatting.
2. **Ruff Linter**: Performs strict syntax, deprecation, and rule analysis.
3. **Mypy Static Analysis**: Validates type signatures, return values, and parameters.

### Manual Verification Commands

You can trigger formatting and typing checks manually at any time:

```bash
# Run style and quality checks on a file
ruff check scratch/tests/test_ai_engine.py --fix
ruff format scratch/tests/test_ai_engine.py

# Run static type checks across the codebase
mypy scratch/tests/test_ai_engine.py
```

---

## 🔍 Troubleshooting & Edge Cases

### 1. Legacy Type Hints (`typing.List` / `typing.Dict`)
* **Problem**: `ruff` throws a `UP035` warning regarding legacy uppercase typing references.
* **Resolution**: Replace legacy `typing.List` and `typing.Dict` with standard `list` and `dict` types.

### 2. Generator Functions and Mypy
* **Problem**: Mypy throws a return type error on test fixtures: `"The return type of a generator function should be 'Generator' or one of its supertypes"`.
* **Resolution**: Annotate the yield fixture with `collections.abc.Generator` rather than `-> None`:
  ```python
  from collections.abc import Generator
  import pytest

  @pytest.fixture
  def temp_db() -> Generator[None, None, None]:
      # Setup
      yield
      # Teardown
  ```

### 3. Pydantic / GenAI Mock Key Mismatch
* **Problem**: Mocking `google.genai.Client` throws serialization errors like `KeyError: 'body'`.
* **Resolution**: Patch the local module-level reference `"services.research_service.genai"` completely inside `test_research.py` to bypass Pydantic construction for type configs, and supply mock dicts containing all required structure keys (`{'title', 'href', 'body'}`).
