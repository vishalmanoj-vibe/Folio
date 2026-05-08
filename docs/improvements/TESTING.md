# Testing Guide

## Running Tests

This project includes comprehensive unit tests for core modules.

### Setup

First, install dependencies:

```bash
pip install -r requirements.txt
```

### Automated Testing Status ⚠️

The automated test suite is currently being refactored to align with the new **SQLite Relational Architecture** and **Single Refresh Owner** pattern. Legacy tests for CSV handlers and older portfolio builders have been decommissioned.

**Planned Test Suite:**
- `test/test_repository.py`: CRUD operations for transactions and asset metadata.
- `test/test_engine.py`: Aggregation logic and P&L math.
- `test/test_signals.py`: Technical indicator accuracy and strategy engine scoring.

To run the (pending) new suite:
```bash
pytest
```

### Manual Verification (Core Features)

For features with complex UI interactions or AI components, follow these manual verification steps to ensure system integrity:

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html test/
```

This generates an HTML coverage report in `htmlcov/index.html`.

1. **SQLite Integrity**:
   - Add a transaction via the UI (Intelligence Modal).
   - Verify it appears in the Portfolio table immediately.
   - Restart the app and verify the transaction persisted in `portfolio.db`.

2. **Technical Indicators**:
   - Navigate to the **Positions** page and verify technical badges (RSI/MACD) match expected trends.
   - Verify color coding: RSI < 30 (Teal/Bullish), RSI > 70 (Red/Bearish).

3. **Market Status**:
   - Verify the "Market Open/Closed" badge correctly reflects AEST time (taking into account the ASX closing auction until 16:15).

## Manual Verification (UI Features)

For features with complex UI interactions or AI components, follow these manual verification steps:

### Technical Indicators (Intelligence Page)
1. Navigate to the **Intelligence** page.
2. Verify the "Technical Signals" table renders for all holdings.
3. Cross-check the RSI values against a third-party source (e.g., Yahoo Finance or TradingView) to ensure Wilder's smoothing is accurate.
4. Verify color coding: RSI < 30 (Green), RSI > 70 (Red).

### Candlestick Charts (Positions Page)
1. Navigate to the **Positions** page and select an ETF.
2. Toggle between different time periods (1mo, 6mo, 1y).
3. Verify that the Candlestick chart renders correctly for periods > 1d.
4. Verify that for the **1d** period, the chart gracefully falls back to a Scatter (Line) chart to handle missing OHLC data.

### AI Research Context (Research Page)
1. Navigate to the **Research** page.
2. Enter a ticker in the input field.
3. Send a query (e.g., "Analyze my portfolio").
4. Verify the AI response incorporates technical status (e.g., "I see VAS is currently in an oversold state with an RSI of 28").

## Future Test Coverage
1. **test_technical_indicators.py** (Planned): Unit tests for RSI, MACD, and BB math using fixed price series.
2. **test_period_sync.py** (Planned): Verification of the "Global Max Period" logic in `app.py`.

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
