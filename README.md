# Folio

A local portfolio dashboard for tracking ASX ETFs with live prices, P&L history, dividends, deep-dive analytics, and AI-powered insights.

Built with Dash, Plotly, yfinance, and Gemini.

![Dashboard](screenshots/screenshot.png)

## Features

- **Live Tracking** — Real-time prices via Yahoo Finance with ASX-specific bulk optimisations and 5-minute refresh.
- **Intraday Monitoring** — "Today" P&L chart with high-frequency session caching and persistent daily snapshots across restarts.
- **Positions Deep-Dive** — Candlestick charts, transaction history, live sparklines, and integrated dividend analysis per holding.
- **Insights Dashboard** — Sharpe Ratio, Annualised Volatility, Max Drawdown, and equity curve with optional Prophet forecasting.
- **Allocation Analysis** — Hierarchical Sector and Geographic treemaps with smart concentration alerts.
- **Dividend Tracking** — Tranche-accurate realized income engine matched against actual ex-dividend dates, not just yield estimates.
- **Trading Signals** — Weighted BUY/SELL/HOLD engine using trend, momentum, drawdown, moving averages, and cost basis analysis. Includes optional AI-generated explanations.
- **Watchlist** — Track tickers you don't own yet with live pricing, signals, and research notes.
- **AI Assistant** — Chat interface powered by Gemini 2.5 Flash Lite for portfolio analysis and ticker research, with persistent conversation memory and optional web search.
- **Weekly PDF Report** — AI-generated portfolio summary with holdings breakdown, technical signals, dividend calendar, and market news.
- **Premium Aesthetics** — High-fidelity UI with glassmorphism navigation, smooth 200ms theme transitions, Inter typography (tabular numerals), and interactive hover depth.
- **Data Freshness Heartbeat** — Real-time animated status indicator in the header synchronized with ASX trading sessions.

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Clone the repo
git clone https://github.com/vishalmanoj-vibe/folio.git
cd folio

# 2. Create and activate a virtual environment
python -m venv folio-env
source folio-env/bin/activate      # Mac/Linux
folio-env\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add a .env file for AI features (optional)
echo "GEMINI_API_KEY=your_key_here" > .env

# 5. Run
python launcher.py
# This starts both the Dash UI and the background worker.
# Open manually at http://127.0.0.1:8050
```

The database is created automatically on first run. Add your transactions directly from the UI — no CSV or manual setup required.

## AI Features

The AI Assistant and Trading Signal AI overlay both require a Gemini API key. Get one free at [aistudio.google.com](https://aistudio.google.com).

All other features (live prices, P&L tracking, dividends, signals engine, forecasting) work without an API key.

## Pages

| Page | Route | Description |
|---|---|---|
| Holdings | `/` | Live positions table, P&L chart, stat cards |
| Positions | `/positions` | Per-holding deep-dive with candlestick charts and dividends |
| Watchlist | `/watchlist` | Track tickers you are considering buying |
| Insights | `/intelligence` | Risk metrics, equity curve, drawdown, forecasting |
| Deep Dive | `/analytics` | Allocation treemaps, correlation matrix, volatility |
| Assistant | `/ai-analyst` | Chat-based portfolio research and weekly PDF report |

## Architecture

- **Orchestration** →  `launcher.py` (Process Manager), `worker.py` (Background Service)
- **Presentation**   →  `app.py`, `pages/`, `callbacks/`, `components/`, `assets/`
- **Service**        →  `services/market/`, `services/ai_engine.py`, `services/strategy_engine.py`, `services/intelligence_service.py`
- **Engine**         →  `core/engine/portfolio_engine.py`, `core/engine/stats_engine.py`
- **Data**           →  `data/repository.py`, `data/database.py` (SQLite Relational Persistence)

All market data fetches use `yf.download()` bulk calls — never per-ticker loops. The database uses WAL mode for safe concurrent writes from the background snapshot thread.

For a full breakdown of the data flow, callback architecture, and module responsibilities see the [Developer Guide](docs/guides/DEVELOPER_GUIDE.md).

## Tech Stack

| Layer | Libraries |
|---|---|
| UI | Dash, Dash Mantine Components, Dash Bootstrap Components, Plotly |
| Data | yfinance, pandas, SQLite |
| AI | Google Gemini 2.5 Flash Lite (google-genai) |
| Forecasting | Facebook Prophet |
| Reports | ReportLab, Matplotlib |
| Search | DuckDuckGo Search (ddgs) |

## Disclaimer

Folio started as a personal project to solve real portfolio tracking problems while experimenting with modern AI-assisted development tools. Approximately 70% of this codebase was generated using AI; as such, users should expect occasional bugs and are encouraged to verify critical data.

This dashboard is for personal tracking only. Nothing it displays constitutes financial advice. Always verify with a licensed financial adviser before making investment decisions.

If you plan to contribute or want to understand the data flow, please read the Developer Guide for a complete breakdown of the UI, Services, Data, and Core layers.

## Data Source

Market data is sourced from Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance). 
This data is intended for personal use only. Commercial use of Yahoo Finance 
data requires a separate data agreement with Yahoo. See 
[Yahoo Finance Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) 
for details.

## License

MIT License © 2026 Vishal Manoj Kumar