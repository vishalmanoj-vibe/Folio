# High-Performance Isolated Testing Guide

Folio includes a world-class, automated test and code quality framework. All unit tests run in **completely offline, sandbox-isolated environments** to ensure fast, deterministic, and network-free execution.

---

## 🏗️ Core Testing Principles

1. **Zero-Network Isolation**: No test is allowed to trigger real Yahoo Finance downloads, DuckDuckGo searches, or Google Gemini API requests. Everything is strictly mocked.
2. **Database Cleanliness**: Tests interact with isolated, fresh in-memory or temporary SQLite databases. The main `portfolio.db` is never read or written to during testing.
3. **Modern Type Safety**: All files are strictly typed. We use modern, non-deprecated Python 3.9+ type declarations (e.g. standard `list` and `dict` rather than `typing.List` and `typing.Dict`).
4. **Strict Style Compliance**: Every test suite and application file must pass `ruff` format and lint checks, as well as strict `mypy` static analysis.

---

## 📁 Test Architecture & Layout

All unit tests are organized inside the `scratch/tests/` directory to prevent codebase clutter:

```text
scratch/
├── run_tests.sh              # Unified Test Runner
└── tests/
    ├── test_ai_engine.py             # Analyst overlay, verdict mapping, client mocks
    ├── test_chart_components.py     # go.Figure builders (PnL history, allocations, etc.)
    ├── test_dividend_service.py     # Tranche matching, ex-date eligibility, yield calculations
    ├── test_repository.py           # SQLite WAL connections, transactions CRUD
    ├── test_research.py             # Gemini context builder, log pruning, smart searches
    ├── test_strategy_engine.py       # Deterministic signal scores, flip prevention
    ├── test_technical_indicators.py  # Pure pandas RSI, MACD, and Bollinger Bands
    └── test_ui_callbacks.py         # Dash state updates, URL-prioritized page routing
```

### Coverage Overview & Deep-Dives

Our 9 primary test suites cover the core business math, data layers, and visual rendering paths:

| Test Suite | File Path | Focus Area |
| :--- | :--- | :--- |
| **Dividend Engine** | `scratch/tests/test_dividend_service.py` | Validates transaction tranche ex-date calculations to prevent "phantom income". |
| **AI Analyst Engine** | `scratch/tests/test_ai_engine.py` | Tests Gemini response parsing, confidence thresholds, and `VERDICT_MAP` normalization. |
| **Persistence Repos** | `scratch/tests/test_repository.py` | Tests SQLite setup, WAL concurrent pragmas, transactional rollbacks, and watchlist notes. |
| **Visual Charts** | `scratch/tests/test_chart_components.py` | Verifies Plotly `go.Figure` structures, theme token variables, and `create_empty_fig` fallback states. |
| **Research Assistant** | `scratch/tests/test_research.py` | Mocks Gemini context generation, smart web search token triggers, and rolling log summaries. |
| **Strategy Engine** | `scratch/tests/test_strategy_engine.py` | Checks weighted BUY/SELL/HOLD scores, hysteresis flip preventions, and CGT tranche warnings. |
| **Technicals Math** | `scratch/tests/test_technical_indicators.py` | Validates custom pandas formulas for RSI (Wilder's), MACD, and Bollinger Bands. |
| **UI & Callbacks** | `scratch/tests/test_ui_callbacks.py` | Checks metric aggregation cards and prioritized background URL routing protection. |

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
