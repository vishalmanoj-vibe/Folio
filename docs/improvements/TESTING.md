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
   - Add a transaction via the UI (Holdings page transaction form).
   - Verify it appears in the Holdings table immediately.
   - Restart the app and verify the transaction persisted in `portfolio.db`.

2. **Technical Indicators & Signals**:
   - Navigate to the **Positions** page, select a ticker, and click "Generate Signals".
   - Verify that the signal badge (BUY/SELL/HOLD) and the AI Assistant insight card appear.
   - Navigate back to the **Holdings** page and verify the "Suggestion" column in the main table matches the signal.

3. **Deep Dive Visualization**:
   - Navigate to the **Deep Dive** page.
   - Verify that Treemap charts (Allocation tab) blend seamlessly with the background (no grey canvas).
   - Toggle between Flat Tickers / Sector / Region and verify hierarchy updates.

4. **Market Status & Intraday**:
   - Verify the "Market Open/Closed" badge correctly reflects AEST time (taking into account the ASX closing auction until 16:15).
   - Check the "Today" (1d) chart and verify it displays 5-minute resampled data with no overnight gaps.

6. **Memory Hygiene & Distributed Worker**:
   - Open a system monitor (e.g., Activity Monitor or `top`).
   - Run `python launcher.py` and verify the `app.py` process stays around **300-350MB**.
   - Navigate to the **ETF Details** page for a ticker requiring scraping (e.g., a new ETF).
   - Verify that the UI displays "Scraping in progress" and that the RAM spike happens in the **worker.py** process, NOT the `app.py` process.
   - Verify that clicking "Refresh" on a ticker with < 1 year of history does NOT trigger a redundant yfinance call if it was already fetched (Smart Depth check).

7. **Visual Stability**:
   - Navigate to the **Analytics** page.
   - Hover over the Normalized Price chart.
   - Verify that the hover labels appear correctly without any "Error in f-string" console artifacts (Stable Hover Fix).

## Manual Verification (UI Features)

For features with complex UI interactions or AI components, follow these manual verification steps:

### Technical Signals (Insights Page)
1. Navigate to the **Insights** page.
2. Verify the Risk metrics cards render correctly.
3. Verify that the "Forecast" toggle (Prophet) adds the projection line with continuity correction.

### Candlestick Charts (Positions Page)
1. Navigate to the **Positions** page and select an ETF.
2. Toggle between different time periods (1mo, 6mo, 1y).
3. Verify that the Candlestick chart renders correctly for periods > 1d.
4. Verify that for the **1d** period, the chart gracefully falls back to a Scatter (Line) chart.

### AI Assistant Context (Assistant Page)
1. Navigate to the **Assistant** page.
2. Enter a ticker in the research input or use a quick prompt chip.
3. Verify the AI response incorporates technical status and portfolio context.
4. Click "Generate Weekly Report" and verify the PDF download starts.

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
