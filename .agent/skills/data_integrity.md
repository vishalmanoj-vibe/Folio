# Skill: Data Integrity (Market & Portfolio)

## Objective
Ensure the dashboard displays accurate, real-time financial data without crashing during off-market hours or failing due to API data structure changes.

## Rules of Engagement
- **Bulk Downloads Only**: Never use `yf.Ticker(t).info` in a loop. Use `yf.download(tickers)` for performance.
- **MultiIndex Awareness**: Always handle the `(Ticker, Metric)` structure returned by bulk downloads.
- **Timezone First**: All calculations must be pinned to `Australia/Sydney`.

## Core Patterns

### 1. The ASX Price Fallback
Yahoo Finance often returns `0.0` for `last_price` during ASX off-hours.
```python
# pattern in services/market/fetcher.py
price = fast_info['last_price']
if price == 0 or price is None:
    # Fallback to last historical close
    price = hist['Close'].iloc[-1]
```

### 2. MultiIndex Extraction
```python
# pattern in core/utils.py or similar
def _extract_close(df):
    """Safely extracts Close prices from yfinance MultiIndex DataFrame."""
    if isinstance(df.columns, pd.MultiIndex):
        return df.xs('Close', axis=1, level=1)
    return df['Close']
```

### 3. Intraday Sanitization
Avoid "cliff" drops in charts when the first data point of the day is missing or zero.
```python
def sanitize_intraday(df):
    # Forward fill missing values
    df = df.replace(0, np.nan).ffill()
    # Remove any leading NaNs
    return df.dropna()
```

### 4. Dividend Confirmation
Yahoo Finance ex-dates are sometimes unreliable for ASX ETFs.
- Use `CONFIRMED_PAYOUTS` mapping in `dividend_service.py`.
- Ensure `VHY` and `IOZ` dates align with official ASX announcements.

## Verification
- Run `python scripts/test_data_fetch.py` if available.
- Check logs for "Zero price detected for ticker XXX" warnings.
- Verify total portfolio value matches expected magnitude (no sudden 99% drops).
