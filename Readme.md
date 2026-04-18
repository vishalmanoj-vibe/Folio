# Portfolio Dashboard — Live P&L

A local web dashboard for tracking an ASX ETF portfolio with live prices,
P&L history, dividends, and correlation analysis.

Built with Dash, Plotly, and yfinance.

![Dashboard](screenshot.png)

## Features
- Live prices via Yahoo Finance (yfinance)
- Unrealised P&L from purchase date, per tranche
- Today's P&L, day high/low
- Annual dividend income and yield
- Portfolio allocation donut chart
- Return correlation heatmap
- Add buy/sell transactions from the UI — saves to CSV
- Dark/light theme toggle
- PDF export

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