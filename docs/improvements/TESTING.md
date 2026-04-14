# Testing Guide

## Running Tests

This project includes comprehensive unit tests for core modules.

### Setup

First, install test dependencies:

```bash
pip install -r requirements.txt
```

Tests require `pytest` and `pytest-cov` (included in requirements.txt).

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest test/test_portfolio_builder.py -v
```

### Run Specific Test Class or Function

```bash
# Run single test class
pytest test/test_portfolio_builder.py::TestBuildHoldings -v

# Run single test function
pytest test/test_portfolio_builder.py::TestBuildHoldings::test_single_buy_creates_holding -v
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html test/
```

This generates an HTML coverage report in `htmlcov/index.html`.

## Test Modules

### test_portfolio_builder.py

Tests for:
- `validate_transaction()` — Transaction validation with edge cases
- `build_holdings()` — Holdings aggregation from buy/sell transactions

**Key test cases:**
- Valid buy/sell transactions
- Type validation (numeric checks, date formats)
- Buy/sell aggregation logic
- Fully-sold position exclusion
- Invalid transaction filtering

### test_alert_service.py

Tests for:
- `check_alerts()` — Alert condition detection
- Configurable thresholds
- Individual and portfolio-level alerts

**Key test cases:**
- Alert triggering at threshold
- Custom threshold handling
- Multiple alerts from same portfolio
- Edge cases (zero cost basis, missing fields)

### test_csv_handler.py

Tests for:
- `load_csv()` — CSV loading and parsing
- `save_csv()` — CSV writing with backup

**Key test cases:**
- Column name normalization
- Date format auto-detection (YYYY-MM-DD and DD.MM.YYYY)
- Type defaulting to 'buy'
- Error handling (missing files, invalid data)
- Backup creation on write

### test_market_status.py

Tests for:
- `is_market_open()` — Configurable market hours detection
- `market_badge()` — UI status display

**Key test cases:**
- Trading hours detection (10:00-16:00 AET)
- Weekend/holiday handling
- Boundary time cases (exactly at open/close)

## Configuration for Testing

Environment variables for tests can be set in `.env`:

```bash
LOG_LEVEL=DEBUG  # More verbose logging during tests
API_MAX_RETRIES=1  # Faster API timeout during tests
```

## CI/CD Integration

To add tests to your CI pipeline:

```bash
pytest --cov=. --cov-report=xml test/
```

This generates an XML report for integration with GitHub Actions, GitLab CI, etc.

## Troubleshooting

**Import errors?**
Make sure you're running pytest from the project root directory.

**Tests pass locally but fail in CI?**
Check that environment variables are properly set in your CI configuration.

**Flaky tests with yfinance?**
Tests that mock `datetime` may be timezone-sensitive. See `test_market_status.py` for examples of proper mocking.
