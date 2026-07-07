# Folio

A privacy-first investment dashboard for tracking ASX ETFs and stocks. Folio runs entirely on your machine — your transactions live in a local SQLite file, not on someone else's server. It pulls live prices from Yahoo Finance, breaks down ETF holdings so you can see what you actually own, tracks dividends you've earned based on when you bought, and provides BUY/SELL/HOLD signals backed by a deterministic scoring engine. There's also an AI assistant (Gemini, Claude, or ChatGPT) that can explain what the numbers mean and pull in recent financial news.

Built with Python, Dash, Plotly, yfinance, and the Google GenAI SDK.

![Dashboard](screenshots/screenshot.png)

---

## Installation

Folio manages its own environment. The installer downloads everything it needs — you just need Git and an internet connection.

### macOS / Linux

Prerequisites: macOS 12+ or Linux.

1. Open Terminal (`Cmd + Space`, search "Terminal").
2. Clone and enter the repo:
    ```bash
    git clone https://github.com/vishalmanoj-vibe/folio.git
    cd folio
    ```
3. Run the installer:
    ```bash
    ./scripts/install.command
    ```
    You can also double-click `scripts/install.command` in Finder.

### Windows

Prerequisites: Windows 10/11.

1. Open PowerShell as Administrator.
2. Clone and enter the repo:
    ```powershell
    git clone https://github.com/vishalmanoj-vibe/folio.git
    cd folio
    ```
3. Run the installer:
    ```powershell
    scripts\install.bat
    ```
    You can also double-click `install.bat` in the `scripts/` folder.

### What the installer does

Behind the scenes, the script:

- Downloads **uv** (a fast Python package manager) and sets up an isolated `.venv/` environment with Python 3.12.
- Installs all dependencies from [requirements.txt](requirements.txt).
- Installs Playwright WebKit — a headless browser used to scrape ETF holdings when direct APIs aren't available.
- Prompts for a Gemini API key (optional). You can configure keys for Gemini, Claude, and ChatGPT later — see the [AI Provider API Keys Guide](docs/guides/AI_PROVIDERS.md).
- Places a launch shortcut on your Desktop.

---

## Launching the App

After installation, you have three options:

- **Desktop shortcut (recommended):** Double-click the **Folio** shortcut on your Desktop. It starts background tasks and opens `http://127.0.0.1:8050` in your browser.
- **Command line:** Navigate to the project folder and run:
    ```bash
    uv run python launcher.py
    ```
- **Native macOS app:** Double-click **Folio.app** in the project folder. It starts the server silently — open `http://127.0.0.1:8050` manually.

---

## How It Works

Online trackers store your financial data on their servers. Folio doesn't — your transactions and portfolio history stay in a SQLite file on disk. Market data is fetched from Yahoo Finance when needed, processed locally, and cached to keep things fast.

To stay responsive, Folio uses a two-process architecture orchestrated by a launcher. The Dash web app handles the UI, while a separate background worker handles the heavy lifting — downloading prices, scraping ETF metadata, computing signals, and querying AI providers. Both processes read from and write to the same local database using SQLite's Write-Ahead Logging mode.

```text
┌────────────────────────────────────────────────────────┐
│                   YOUR WEB BROWSER                     │
│         (The interactive dashboard you see)            │
└──────────────────────────▲─────────────────────────────┘
                           │ (Runs locally on localhost:8050)
                           ▼
┌────────────────────────────────────────────────────────┐
│                   FOLIO LAUNCHER                       │
│    (Orchestrates the two parts below to run smoothly)   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│       DASH WEB APP          │    │      BACKGROUND WORKER      │
│  • Listens to click events  │    │  • Fetches live stock prices│
│  • Renders beautiful charts │    │  • Scrapes ETF companies    │
│  • Manages page navigation  │    │  • Computes BUY/SELL signals│
└──────────────┬──────────────┘    └──────────────┬──────────────┘
               │                                  │
               └────────────────┬─────────────────┘
                                │ (Saves & Reads Data)
                                ▼
                    ┌──────────────────────────┐
                    │    LOCAL DATABASE FILE   │
                    │    (data/portfolio.db)   │
                    │   *Stays on your computer*│
                    └──────────────────────────┘
```

The four components in detail:

1. **The Launcher ([launcher.py](launcher.py))** starts the Dash app and the background worker as subprocesses, monitors their health, and intercepts OS signals to prevent orphan processes on exit.
2. **The Dash Web App ([app.py](app.py))** serves the interactive UI. It boots from cached database snapshots so pages render quickly, then defers the first live market data fetch to a startup interval.
3. **The Background Worker ([worker.py](worker.py))** runs a dedicated task loop for I/O-bound and CPU-heavy work: downloading tickers, scraping ETF metadata, calculating technical indicators, and querying the Gemini API.
4. **The Database ([data/portfolio.db](data/portfolio.db))** is SQLite configured with WAL mode, a 5-second busy timeout, and synchronous `NORMAL` writes — this allows the UI and worker to read and write concurrently without stepping on each other.

---

## What's on Each Page

Folio has a glassmorphic sidebar menu linking to six pages.

### Portfolio Holdings (Home)

The landing page shows your net worth, total cost, today's P&L, and overall P&L at a glance. Below the summary cards is a holdings table listing each ticker with news sentiment and signal suggestions, alongside a real-time intraday P&L chart. The chart fetches a 2-day history at 5-minute intervals to stitch the final hour of the previous trading session, and uses Plotly `rangebreaks` to hide weekends and overnight gaps. A status dot in the header pulses green during ASX trading hours.

### Positions Deep-Dive (`/positions`)

Pick any ticker to see its candlestick price chart (OHLC) over multiple time intervals, your individual purchase tranches with date, cost, and P&L for each, historical and projected dividend payouts mapped to the tranches that actually qualify, and an AI-generated analysis card. The dividend engine compares each tranche's purchase date against ex-dividend dates to figure out exactly which payouts you're entitled to.

### Watchlist (`/watchlist`)

Track assets you're considering before buying. Each row shows the current price, news sentiment, and a signal recommendation. Click any item to view its historical chart and write research notes. You can reorder rows by dragging the `☰` grab handles — this is handled by a vanilla JavaScript handler ([drag_drop.js](assets/drag_drop.js)) that persists the new order back to the database.

### Intelligence & Risk (`/intelligence`)

This page runs the maths on your portfolio's risk profile: volatility, Sharpe ratios, and peak-to-trough drawdowns. It includes an equity curve showing historical portfolio performance and an ML-powered price forecast. Forecasts are computed by Facebook Prophet in the background worker and written to `data/cache/predictions.json` so they don't block the UI — the chart renders them with an 80% confidence interval.

### Deep Dive Allocation (`/analytics`)

See where your money actually ends up. ETFs hold hundreds of underlying companies, and Folio scrapes the fund provider's site to build a weighted breakdown. The page shows sector treemaps, geographic exposure maps, and a correlation matrix heatmap (Pearson correlation on daily log returns) so you can see whether your holdings are all moving together.

### Settings (`/settings`)

Configure your investment goal (passive income, high growth, etc.), risk profile (conservative, moderate, aggressive), and marginal tax bracket. These feed into the strategy engine to adjust signal weights and into the AI assistant to tailor its prompts.

---

## Financial Terms & Math Reference

A quick reference for the financial terms used throughout the dashboard, alongside their exact implementation in the code.

| Term | What it means | How Folio calculates it |
| :--- | :--- | :--- |
| **Ticker Symbol** | A short code representing a stock or fund (e.g. `VAS` = Vanguard Australian Shares). | Stored without suffixes in SQLite. The market data layer appends `.AX` dynamically for yfinance requests. |
| **ETF** | A basket of company shares bundled into a single tradeable package. | Scraped via a 3-tier architecture in [holdings_fetcher.py](services/market/holdings_fetcher.py): Tier 1 (direct API), Tier 1.5 (DuckDuckGo URL discovery), Tier 2 (headless Playwright). Holdings are cached with a 7-day staleness check. |
| **P&L (Profit & Loss)** | The money you've gained or lost compared to what you paid. | Total P&L aggregates across purchase tranches. Intraday P&L uses 5-minute resampled snapshots restricted to Sydney market hours (10:00–16:15) to hide overnight gaps. |
| **Tranche** | A specific batch of shares bought at one time. | Stored in the `transactions` table with `price`, `units`, and `date`. If any tranche has been held < 365 days, the strategy engine appends a CGT discount warning to SELL recommendations. |
| **Ex-Dividend Date** | The cutoff — you must own shares *before* this date to receive the payout. | [dividend_service.py](services/market/dividend_service.py) compares `purchase_date < ex_dividend_date` per tranche to compute realised cash flows. |
| **Sharpe Ratio** | A score measuring whether your returns justify the risk you're taking. | $$\text{Sharpe} = \frac{\overline{R_p} - R_f}{\sigma_p} \times \sqrt{252}$$ where $\overline{R_p}$ is the mean daily log return, $\sigma_p$ is its standard deviation, and $R_f$ is a 4.35% annualised risk-free rate proxy. Calculated in [intelligence_service.py](services/intelligence_service.py). |
| **Volatility** | How much a stock's price bounces around. | Annualised standard deviation of daily log returns: $\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252}$. |
| **Correlation Matrix** | A grid showing whether your investments rise and fall together. | Pearson correlation via pandas `.corr()` on daily log returns over a 1-year rolling window. |
| **Forecasting (Prophet)** | A statistical projection of where your portfolio value is heading. | Uses Facebook Prophet's additive model ($y(t) = g(t) + s(t) + h(t) + \epsilon_t$) in [prediction_service.py](services/prediction_service.py) with a continuity drift correction at the historical boundary: $\text{forecast}_{\text{corrected}} = \text{forecast} + (y_{\text{actual}} - y_{\text{fitted}})$. |
| **RSI** | Momentum score (0–100). Above 70 = overbought, below 30 = oversold. | Wilder's RSI via EWMA with `com=N-1` (N=14) on gains and losses. Implemented in [technical_indicators.py](services/technical_indicators.py). |
| **MACD** | Trend-following indicator showing the relationship between two moving averages. | Returns `(MACD line, Signal line)` where MACD = $EMA_{12} - EMA_{26}$ and Signal = $EMA_9(\text{MACD})$. |
| **Bollinger Bands** | Volatility bands above and below a moving average. | $SMA_{20} \pm 2\sigma_{20}$ — the 20-day simple moving average plus/minus two rolling standard deviations. |

---

## Strategy Engine

Folio includes a deterministic strategy engine ([strategy_engine.py](services/strategy_engine.py)) that scores each asset on a scale of -1.0 (strong sell) to +1.0 (strong buy) using five weighted dimensions:

1. **Trend (35%):** Alignment of 20-day and 50-day simple moving averages.
2. **Momentum (20%):** Standardised RSI and MACD signal crossovers.
3. **Value (15%):** Current price distance from the 200-day SMA.
4. **Cost Basis (15%):** Your average purchase cost relative to the current price.
5. **Risk (15%):** Asset volatility relative to market benchmarks.

```
       SELL               HOLD               BUY
[ -1.0 ◄─────► -0.5 ] [ -0.5 ◄─────► +0.5 ] [ +0.5 ◄─────► 1.0 ]
         │                                      │
         └───────────── Hysteresis ─────────────┘
          (Requires absolute score of >=0.7
           to flip an existing trend signal)
```

Scores at or above 0.5 issue a BUY, at or below -0.5 issue a SELL, and everything in between stays HOLD. To prevent flickering on volatile days, an existing signal can't flip unless the new score exceeds 0.7 in absolute terms — when this kicks in, `hysteresis_forced: True` gets flagged in the database. If a SELL signal triggers on an asset where any tranche has been held less than a year, the engine appends a capital gains tax discount warning.

---

## AI Assistant

The chatbot widget in the bottom-right corner is a portfolio-aware research assistant. It knows your holdings, understands the strategy engine's signals, and can pull in recent financial news.

```
┌────────────────────────┐      ┌────────────────────────┐
│      USER MESSAGE      ├─────►│  RESEARCH COORDINATOR  │
│  (e.g., "Why is VAS    │      │ (research_service.py)  │
│    dropping today?")   │      └───────────┬────────────┘
└────────────────────────┘                  │ (Check keywords & trigger search)
                                            ▼
┌────────────────────────┐      ┌────────────────────────┐
│   GEMINI AI CRITIQUE   │◄─────┤   DUCKDUCKGO SEARCH    │
│    (ai_engine.py)      │      │  (ddgs financial news) │
└───────────┬────────────┘      └────────────────────────┘
            │ (Normalise verdict & apply cache)
            ▼
┌────────────────────────┐
│  PORTFOLIO-AWARE CHAT  │
│ (cites news / sources) │
└────────────────────────┘
```

A few design decisions worth noting:

- **The engine is the source of truth.** The AI ([ai_engine.py](services/ai_engine.py)) explains and critiques the strategy engine's signals — it doesn't generate its own. It can't override a BUY or SELL recommendation.
- **Caching to manage API costs.** AI analyses are cached for 24 hours. The cache key is an MD5 hash of *stable* signal data (verdict + rounded score), ignoring volatile live price ticks. This prevents every price update from burning an API call:
    ```python
    cache_key = "ai_signal_" + md5(json.dumps(stable_signals, sort_keys=True)).hexdigest()
    ```
- **Verdict normalisation.** All AI responses are mapped through `VERDICT_MAP` to exactly three values: `Confident`, `Mixed`, or `Risk flagged`. A tone sanitiser strips LLM verbosity before anything hits the database.
- **Live web search.** When the research coordinator detects financial news keywords in your message, it searches for recent Australian business news via DuckDuckGo (5-second timeout) and feeds the articles into the prompt context. Sources are cited in the chat.
- **Memory management.** Chat history is logged for 7 days in `conversation_log.json`. On startup, older logs are distilled into a bulleted summary in `memory_summary.json` to keep the context window small. A daily message limit (20) and storage ceiling (50MB) are enforced.

---

## Troubleshooting

**macOS permission error:** If the installer won't run, make it executable:
```bash
chmod +x scripts/install.command
```

**macOS Gatekeeper block:** If you see an "unidentified developer" warning, right-click (`Ctrl + Click`) the script, select **Open**, then click **Open Anyway**.

**Windows execution policy block:** If PowerShell blocks the script, open PowerShell as Administrator and run:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Database locking:** Cloud sync clients (OneDrive, iCloud, Dropbox) can lock `portfolio.db` during writes, causing SQLite errors. Move the project folder outside your sync directory.

**Port 8050 in use:** Kill the existing process:
- macOS: `lsof -ti:8050 | xargs kill -9`
- Windows: `for /f "tokens=5" %a in ('netstat -ano ^| findstr :8050') do taskkill /PID %a /F`

**Orphaned processes:** If background tasks seem stuck:
```bash
ps aux | grep -E "app.py|worker.py"
```

For more, see the [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md).

---

## Project Structure

```
folio/
│
├── launcher.py                     # Process manager (starts app.py + worker.py)
├── worker.py                       # Background worker (prices, scraping, AI)
├── app.py                          # Dash app entry point (stores & routing)
│
├── config/                         # Configuration
│   ├── settings.py                 # Env vars, refresh rates, cache TTLs, DB path
│   ├── constants.py                # Colors, static names, themes
│   └── logging.py                  # Logging setup
│
├── core/                           # Foundation layer
│   ├── engine/                     # Pure logic (no I/O)
│   │   ├── portfolio_engine.py     # Aggregation & tranche history
│   │   ├── stats_engine.py         # Summary metrics & UI formatting
│   │   └── utils.py                # Math helpers
│   ├── cache.py                    # TTL cache for API responses
│   └── validators.py               # Transaction schema validation
│
├── models/                         # Domain models
│   └── transaction.py              # Holding & Transaction schemas
│
├── services/                       # Business logic (pure Python, no Dash imports)
│   ├── market/                     # Market data
│   │   ├── data_fetcher.py         # Bulk fetch & enrichment
│   │   ├── dividend_service.py     # Realised dividends & trend logic
│   │   ├── session_cache.py        # Intraday snapshot management
│   │   └── market_status.py        # ASX timezone & market status
│   ├── ai_engine.py                # LLM orchestration & signal critique
│   ├── strategy_engine.py          # Deterministic scoring engine
│   ├── alert_service.py            # Price/target monitoring
│   ├── intelligence_service.py     # Risk & allocation analysis
│   ├── prediction_service.py       # Prophet forecasting
│   ├── report_service.py           # Weekly PDF reports
│   ├── research_service.py         # AI chat & web search
│   └── research_memory.py          # Persistent AI memory
│
├── data/                           # Persistence
│   ├── database.py                 # SQLite connection & schema (WAL)
│   ├── repository.py               # Transaction & asset repository
│   ├── watchlist_repository.py     # Watchlist & history repository
│   ├── portfolio.db                # Main database
│   └── cache/                      # Disk cache (intraday snapshots)
│
├── components/                     # UI components
│   ├── charts/                     # Plotly figure factories
│   │   ├── helpers.py              # Shared layout & empty state builders
│   │   ├── pnl_history.py          # Today's P&L (resampled)
│   │   ├── price_history.py        # Candlestick / line charts
│   │   └── ...
│   ├── header.py                   # Shared navigation header
│   ├── ui_helpers.py               # Stat cards & section wrappers
│   └── chatbot.py                  # Floating AI widget layout
│
├── callbacks/                      # Dash interactivity
│   ├── portfolio_callbacks.py      # Table & metric updates
│   ├── positions_callbacks.py      # Ticker deep-dive logic
│   ├── watchlist_callbacks.py      # Watchlist logic
│   ├── signals_callbacks.py        # Manual signal generation
│   ├── intelligence_callbacks.py   # Modal & drill-down logic
│   └── research_callbacks.py       # AI chat interaction
│
├── pages/                          # Multi-page routing
│   ├── portfolio.py                # Holdings (/)
│   ├── positions.py                # Positions (/positions)
│   ├── watchlist.py                # Watchlist (/watchlist)
│   ├── intelligence.py             # Intelligence (/intelligence)
│   ├── analytics.py                # Deep Dive (/analytics)
│   └── settings.py                 # Settings (/settings)
│
└── assets/                         # Static assets (modular CSS)
    ├── base-tokens.css             # Design tokens (CSS variables)
    ├── base-reset.css              # Global resets
    ├── ui-components.css           # UI blocks (stat cards, etc.)
    └── view-pages.css              # Page-specific overrides
```

### Conventions

A few ground rules that keep things clean:

- **Service layer purity.** Files in `services/` are pure Python — they never import from Dash, callbacks, or pages.
- **Engine layer purity.** Files in `core/engine/` are pure math — no network calls, no file I/O, no library bindings.
- **CSS variables only.** Styles use design tokens from `base-tokens.css` (e.g. `var(--bg)`, `var(--t-pri)`) instead of hardcoded hex values. This keeps light and dark modes consistent.

Standard import patterns:
```python
# Core math (no I/O dependencies)
from core.engine.portfolio_engine import build_holdings, compute_holding_pnl

# Market services (network and database bindings)
from services.market.data_fetcher import fetch_live, get_etf_name

# Data access (database wrappers)
from data.repository import PortfolioRepository
from data.watchlist_repository import WatchlistRepository
```

For deeper documentation:
- [Developer Guide & Architecture](docs/guides/DEVELOPER_GUIDE.md)
- [Architectural Rules (GEMINI.md)](GEMINI.md)
- [Contributing Guide](docs/guides/CONTRIBUTING.md)
- [Testing Guide](docs/testing/TESTING.md)

---

## Testing

Folio uses `pytest` with mock isolation — no tests hit Yahoo Finance or write to your production database.

```bash
# Run the full suite with HTML coverage
./scratch/run_tests.sh

# Open coverage report
open htmlcov/index.html
```

The test runner handles virtual environment paths, runs lints (`ruff` + `mypy` type checking), and exercises 28 test suites covering repositories, calculation models, and Dash callbacks.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **UI** | Dash 2.16+, Dash Mantine Components, Dash Bootstrap Components, Plotly |
| **Database** | SQLite (WAL mode, thread-safe concurrent writes) |
| **Market Data** | yfinance (bulk downloads, 290s intraday cache) |
| **Technical Indicators** | Pure Pandas (Wilder's RSI, MACD, Bollinger Bands) |
| **Forecasting** | Facebook Prophet (ASX trading calendars) |
| **AI** | Google Gemini 2.5 Flash / 3.1 Flash Lite (`google-genai` SDK) |
| **PDF Reports** | ReportLab & Matplotlib |
| **Web Search** | DuckDuckGo Search API (`ddgs` news) |

---

## Disclaimer

Folio started as a personal tracker to solve ASX portfolio management limitations. A significant portion of this codebase was generated using AI tools. You should expect occasional minor bugs and are encouraged to verify critical calculations against your broker statements.

Nothing calculated or displayed by Folio constitutes financial advice. Always consult a licensed financial advisor before making investment decisions.

---

## 📜 License

MIT License © 2026 Vishal Manoj Kumar
