# Portfolio Dashboard — Live P&L

A local web dashboard for tracking an ASX ETF portfolio with live prices,
P&L history, dividends, and correlation analysis.

Built with Dash, Plotly, and yfinance.

![Dashboard](screenshot.png)

## Features
- **Live Tracking**: Live prices via Yahoo Finance (yfinance) with ASX-specific optimizations.
- **P&L Analysis**: Unrealised P&L from purchase date, per tranche, and Today's P&L metrics.
- **Intelligence Dashboard**: Advanced risk metrics (Sharpe, Volatility, Max Drawdown), sector & geographic allocation with Sunburst drill-downs.
- **Portfolio Forecasting**: Prophet-based return predictions with custom confidence intervals and disk-caching.
- **Analytics Page**: Secondary performance metrics, normalized price history, and return correlation heatmaps.
- **Dividend Tracking**: Automatic tracking of annual dividend income, yield, and historical **realized dividends** based on holding dates.
- **Interactive UI**: Add buy/sell transactions via a calendar-based entry system; data persists to CSV.
- **Modular Architecture**: Clean, multi-page Dash structure with modular CSS and a decoupled engine/service model.
- **Modern UI**: Dark/light theme toggle, Radix UI component overrides, and PDF export support.

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/portfolio_dashboard.git
cd portfolio_dashboard

# 2. Create and activate a virtual environment
python -m venv portfolio-env
source portfolio-env/bin/activate      # Mac/Linux
portfolio-env\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your transactions to the CSV
# Edit stock_portfolio_transactions.csv — see format below

# 5. Run
python app.py
# Open http://127.0.0.1:8050
```

## CSV Format

The file `stock_portfolio_transactions.csv` holds all your transactions.
Do not include `.AX` — the app adds it automatically.

## Architecture & Documentation

This project has been heavily refactored for maintainability and scalability. All core modules are thoroughly commented with Google-style docstrings. 

If you plan to contribute or want to understand the data flow, please read the [Developer Guide](docs/guides/DEVELOPER_GUIDE.md) for a complete breakdown of the UI, Services, Data, and Core layers.