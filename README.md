# Folio

A local portfolio dashboard for tracking ASX ETFs with live prices, P&L history, dividends, deep-dive analytics, and AI-powered insights.

Built with Dash, Plotly, yfinance, and Gemini.

![Dashboard](screenshots/screenshot.png)

## Features

- **Live Tracking** — Real-time prices via Yahoo Finance with ASX-specific bulk optimisations and 5-minute refresh.
- **Intraday Monitoring** — "Today" P&L chart with high-frequency session caching and persistent daily snapshots across restarts.
- **Positions Deep-Dive** — Candlestick charts, transaction history, live sparklines, and integrated dividend analysis per holding and globally.
- **Insights Dashboard** — Sharpe Ratio, Annualised Volatility, Max Drawdown, and equity curve with optional Prophet forecasting.
- **Allocation Analysis** — Hierarchical Sector and Geographic treemaps with smart concentration alerts.
- **Dividend Tracking** — Tranche-accurate realized income engine matched against actual ex-dividend dates, not just yield estimates.
- **Trading Signals** — Weighted BUY/SELL/HOLD engine using trend, momentum, drawdown, moving averages, and cost basis analysis. Includes optional AI-generated explanations.
- **Watchlist** — Track tickers you don't own yet with live pricing, signals, and research notes. Supports premium manual drag-and-drop reordering.
- **AI Assistant Chatbot** — Globally-accessible floating chatbot widget powered by Gemini (leveraging Investor Profile settings) for portfolio-aware analysis and ticker research with optional real-time web search.
- **Weekly PDF Report** — AI-generated portfolio summary with holdings breakdown, technical signals, dividend calendar, and market news.
- **Premium Aesthetics** — High-fidelity UI with glassmorphism navigation, smooth 200ms theme transitions, Inter typography (tabular numerals), and interactive hover depth.
- **Data Freshness Heartbeat** — Real-time animated status indicator in the header synchronized with ASX trading sessions.

## Installation

### macOS / Linux

**Requirements:** macOS 12+ or Linux, Git, internet connection (all dependencies and Python version managed automatically).

```bash
# 1. Clone the repo
git clone https://github.com/vishalmanoj-vibe/folio.git
cd folio

# 2. Run the installer (or double-click scripts/install.command in Finder)
./scripts/install.command
```

The installer will:
- Install [uv](https://docs.astral.sh/uv/) (extremely fast Python package manager) if missing
- Download and configure Python 3.12 in a sandboxed, isolated environment
- Install all dependencies from `requirements.txt`
- Install Playwright WebKit (used for ETF holdings data scraping)
- Prompt for your **Gemini API key** and write it to `.env`
- Automatically copy a **`Folio.command`** shortcut to your **Desktop** for one-click launch
- Create **`Folio.app`** in the project folder (macOS native app bundle)

**After install, to launch:**
- **Option 1 (Recommended):** Double-click the **`Folio.command`** file on your Desktop. It will launch the backend processes and automatically open the dashboard in Safari.
- **Option 2:** Open Terminal in the project root and run `uv run python launcher.py`.
- **Option 3 (macOS App):** Open `Folio.app` (drag it to `/Applications` or pin to Dock). Note: this runs the server but doesn't auto-open a browser window.

---

### Windows

**Requirements:** Windows 10/11, Git, internet connection.

```cmd
1. Clone the repo:
   git clone https://github.com/vishalmanoj-vibe/folio.git
   cd folio

2. Double-click scripts\install.bat (or run scripts\install.bat from Command Prompt)
```

The installer will:
- Install [uv](https://docs.astral.sh/uv/) via PowerShell if not present
- Download and configure Python 3.12 in an isolated environment
- Install all dependencies from `requirements.txt`
- Install Playwright WebKit
- Prompt for your **Gemini API key** and write it to `.env`
- Automatically create a **`Folio`** shortcut on your **Desktop** (`Folio.lnk`)

**After install, to launch:**
- **Option 1 (Recommended):** Double-click the **`Folio`** shortcut on your Desktop. It will start the server and automatically open the dashboard in your default browser.
- **Option 2:** Double-click `scripts\folio_launch.bat` in the `scripts/` root folder.
- **Option 3:** Open Command Prompt in the project root and run `uv run python launcher.py`.

---

### Troubleshooting & Common Setup Issues

If you run into issues during installation or launch (such as permissions errors, PowerShell execution blocks, path spaces, OneDrive locks, or Playwright setup failures), please refer to our [Troubleshooting & Common Setup Issues](docs/guides/TROUBLESHOOTING.md) guide.

---

### Gemini API Key (AI Features)

AI features (trading signals overlay, chatbot, weekly PDF reports) require a free Gemini API key.

1. Get your key at [aistudio.google.com](https://aistudio.google.com) — it's free.
2. The installer will prompt you for it automatically.
3. To add/change it later, edit the `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_key_here
   ```

All other features (live prices, P&L tracking, dividends, technical signals, forecasting) work without an API key.
---

### Developer Setup (Manual)

If you want full control over the environment (for contributing or debugging):

```bash
git clone https://github.com/vishalmanoj-vibe/folio.git
cd folio

# Create and activate a virtual environment (Python 3.12 recommended)
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright WebKit
playwright install webkit

# Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# Run
python launcher.py
```

The database (`data/portfolio.db`) is created automatically on first run. Add your transactions directly from the UI — no CSV or manual setup required.

## Testing

Folio features a comprehensive, high-performance unit testing suite built on `pytest`. All tests execute inside mock-isolated environments, completely decoupled from live external APIs or production SQLite database files:

```bash
# Run all fast unit tests and generate coverage report
./scratch/run_tests.sh

# Open the interactive HTML coverage map in your browser
open htmlcov/index.html
```



## Pages

| Page | Route | Description |
|---|---|---|
| Holdings | `/` | Live positions table, P&L chart, stat cards |
| Positions | `/positions` | Per-holding deep-dive with candlestick charts and global portfolio dividend insights |
| Watchlist | `/watchlist` | Track tickers you are considering buying |
| Insights | `/intelligence` | Risk metrics, equity curve, drawdown, forecasting |
| Deep Dive | `/analytics` | Allocation treemaps, correlation matrix, volatility |
| Settings | `/settings` | Investor Profile setup (goal, risk, tax bracket configuration) and dynamic strategy weights |

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
