# Folio

A premium local investment dashboard for tracking ASX ETFs (and stocks) with live prices, profit & loss (P&L) history, ex-dividend tracking, advanced risk analytics, and AI-powered insights.

Built with **Python**, **Dash**, **Plotly**, **yfinance**, and **Google Gemini**.

![Dashboard](screenshots/screenshot.png)

---

## 🧭 For Beginners: What is Folio?

**Folio is a private, local control center for your investments.** 

Unlike online tracking websites that store your private financial data on their servers, Folio runs entirely on your own computer. It is a tool designed to show you exactly how your investments are performing, how your funds are allocated, and what the numbers mean—without compromising your privacy.

### How does it help you?
1. **Tracks Your Money Locally:** All your transactions (buys and sells) are saved in a local database file on your computer.
2. **Sees Inside Your ETFs:** ETFs are like boxes of mixed chocolates—they hold tiny slices of hundreds of different companies. Folio looks *inside* those boxes to tell you exactly how much of your total money is in technology, banking, or specific companies like Apple or BHP.
3. **Calculates Real Dividends:** It tracks exactly when you bought your shares and matches them against ex-dividend dates to show you how much cash you actually made (or are about to make).
4. **Has a Built-In Financial Assistant:** Powered by Google Gemini, a friendly AI Chatbot sits on the side of your screen to answer questions about your holdings, explain technical charts, and search the web for the latest financial news.

---

## 📖 Finance-to-English: Terminology Guide

If you are new to investing, some terms in this dashboard might sound like jargon. Here is a simple guide to what they mean:

| Term | What it means in plain English |
| :--- | :--- |
| **Ticker Symbol** | A 3-to-4 letter code representing a stock or fund on the market. E.g., `VAS` is Vanguard's Australian Shares Index ETF, and `CBA` is Commonwealth Bank of Australia. |
| **ETF (Exchange Traded Fund)** | A basket of many different company shares bundled into a single package. Buying one unit of an ETF spreads your money across hundreds of companies instantly. |
| **P&L (Profit & Loss)** | How much money you have gained or lost on paper compared to what you paid. **Intraday P&L** is how much your value changed *today*, while **Total P&L** is your gain/loss since the day you bought it. |
| **Tranche** | A specific batch of shares bought at one time. If you buy 10 units of `VAS` in January and another 10 in June, you have two separate tranches. Folio tracks them individually to calculate correct taxes and dividends. |
| **Ex-Dividend Date** | The cutoff date for a dividend payout. To receive the upcoming dividend, you must buy and own the shares *before* this date. If you buy on or after this date, the previous owner gets the cash. |
| **Sharpe Ratio** | A score that measures if your portfolio's gains are worth the price swings (volatility) you are experiencing. A higher Sharpe Ratio (above 1.0) means you are getting good returns for the level of risk you are taking. |
| **Volatility** | A measure of how wildly a stock's price bounces up and down. High volatility means the price swings rapidly; low volatility means the price is relatively stable. |
| **Correlation Matrix** | A grid showing if your investments move together. If two stocks have a high correlation, they rise and fall at the same time. Spreading your money across assets with low correlation protects you if one sector crashes. |
| **Forecasting (Prophet)** | An AI model that looks at your historical portfolio performance and calculates a mathematical guess of where your portfolio value might head in the next few months. |

---

## ⚙️ How Folio Works Under the Hood

Folio uses a **Double-Process Architecture** to ensure the user interface remains fast, responsive, and completely lag-free. 

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

1. **The Launcher (`launcher.py`):** When you open Folio, it starts two separate programs in the background. It monitors their health and restarts them if they run out of memory or crash.
2. **The Dash Web App (`app.py`):** This runs the visual dashboard you see in your web browser. It is optimized to load instantly, showing you cached snapshots of your portfolio while the background worker fetches fresh details.
3. **The Background Worker (`worker.py`):** This operates silently in the background, performing the heavy lifting: downloading live prices, running complex math, parsing ETF web data, and managing AI signals.
4. **The Local Database (`data/portfolio.db`):** A lightweight relational database file. It stores your transaction records, your watchlist, and cached stock data so that everything remains accessible offline.

---

## 🚀 Installation & First-Time Setup

Folio manages its own environment automatically. You do not need to install complex software libraries manually.

### 🍏 macOS / Linux

**Prerequisites:** macOS 12+ or Linux, Git, and an internet connection.

1. **Open Terminal** (press `Cmd + Space`, type "Terminal", and press Enter).
2. **Clone this repository** to your computer and navigate into it:
   ```bash
   git clone https://github.com/vishalmanoj-vibe/folio.git
   cd folio
   ```
3. **Run the Installer:**
   ```bash
   ./scripts/install.command
   ```
   *(Alternatively, double-click `scripts/install.command` inside Finder).*

---

###  Windows

**Prerequisites:** Windows 10 or 11, Git, and an internet connection.

1. **Open Command Prompt** or **PowerShell** as an Administrator.
2. **Clone the repository** and navigate into it:
   ```cmd
   git clone https://github.com/vishalmanoj-vibe/folio.git
   cd folio
   ```
3. **Run the Installer:**
   ```cmd
   scripts\install.bat
   ```
   *(Alternatively, double-click the `install.bat` file in the `scripts/` folder inside File Explorer).*

---

### What the Installer Does Behind the Scenes
- Downloads **`uv`** (a super-fast Python tool manager) to isolate the application's environment.
- Configures **Python 3.12** inside a private folder (`.venv/`) so it doesn't affect your computer's global files.
- Installs all dependencies (libraries for plotting, math, and web scraping) listed in [requirements.txt](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/requirements.txt).
- Installs **Playwright WebKit** (a clean, headless browser engine used to scrape underlying ETF company allocations).
- Prompts you for a **Gemini API Key** (optional, used for AI summaries/chat) and writes it securely to a local `.env` configuration file.
- Automatically places a **Folio shortcut on your Desktop** for easy one-click launching in the future.

---

## ⚙️ Launching the Application

After installation, you can run the app in three ways:

*   **Option 1: The Desktop Shortcut (Recommended)**
    Double-click the **`Folio`** shortcut created on your Desktop. It will start the background processes and automatically open the dashboard in your default web browser (Safari, Chrome, Edge, etc.) at `http://127.0.0.1:8050`.
*   **Option 2: The Command Line**
    Navigate to the project directory in Terminal/Command Prompt and run:
    ```bash
    uv run python launcher.py
    ```
*   **Option 3: Native macOS App**
    If on macOS, double-click **`Folio.app`** created in the project folder. You can drag this to your `/Applications` folder or pin it to your Dock. (Note: This starts the server silently. You will need to open your browser manually and visit `http://127.0.0.1:8050`).

---

## 🛠 Troubleshooting Common Issues

*   **macOS Permission Error:** If you get a warning saying *"install.command could not be executed because you do not have appropriate privileges"*, run this command in Terminal to fix it:
    ```bash
    chmod +x scripts/install.command
    ```
*   **macOS Gatekeeper Block:** If macOS blocks the installer or the app as being from an *"unidentified developer"*, right-click (`Ctrl + Click`) the file, select **Open**, and click **Open Anyway** in the prompt.
*   **Windows PowerShell Block:** If Windows blocks the installer from downloading files, open PowerShell as an Administrator and run:
    ```powershell
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
    Then run the installer again.
*   **Database Lock Issues:** If you store the Folio directory inside a cloud sync folder (like **OneDrive**, **iCloud**, or **Dropbox**), the active syncing can lock the database file (`portfolio.db`) and cause errors. Move the `folio/` folder to your home directory (e.g., `/Users/yourusername/folio` or `C:\folio`) to avoid this.
*   **Port 8050 Conflict:** If the app fails to open because port 8050 is in use:
    - *macOS:* Run `lsof -ti:8050 | xargs kill -9` in Terminal.
    - *Windows:* Run `for /f "tokens=5" %a in ('netstat -ano ^| findstr :8050') do taskkill /PID %a /F` in Command Prompt.

*(For detailed solutions, see the [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md)).*

---

## 🗺 Dashboard Feature Tour (Page-by-Page)

Folio features a glassmorphic sidebar navigation menu linking to six specialized dashboard views:

### 1. Portfolio Holdings (Home)
Your primary dashboard screen.
*   **Quick Stats:** View Net Worth, Total Cost, Total P&L ($ and %), and Today's change.
*   **Holdings Table:** A clean list of your active investments. Shows tickers, names, current prices, total cost, current value, total profit/loss, news sentiment, and technical suggestions (BUY/SELL/HOLD).
*   **Today's P&L Chart:** A real-time timeline showing how your portfolio's value has fluctuated today during trading hours, resampled to clean 5-minute ticks with weekends hidden.

### 2. Positions Deep-Dive (`/positions`)
Select any ticker from the sidebar to inspect it individually.
*   **Candlestick Chart:** View historical price bars (Open, High, Low, Close) over 1 Month, 6 Months, 1 Year, or Max timeframes.
*   **Transaction Batches (Tranches):** See exactly when you bought each batch of shares, how many units, at what price, and the individual profit or loss.
*   **Dividend History:** Lists your received dividends for this stock, ex-dividend dates, and annual projected cash flow.

### 3. Watchlist (`/watchlist`)
Track tickers you do not own yet.
*   **Interactive List:** Shows the ticker, current price, today's price change, news sentiment, and buying signal recommendation.
*   **Premium Drag-and-Drop:** Hover over any row, grab the handle (`☰`), and drag to reorder. The custom order is instantly saved to the database and persists across page reloads.
*   **Quick Charting:** Click any watchlist item to view its historical chart and write custom research notes.

### 4. Intelligence & Risk (`/intelligence`)
Advanced mathematical metrics to evaluate your portfolio's risk-reward profile.
*   **Risk Ratios:** Calculates **Annualized Volatility** (how volatile your portfolio is), **Sharpe Ratio** (are your gains worth the price swings?), and **Max Drawdown** (the largest peak-to-trough fall in your portfolio's history).
*   **Equity Curve:** Plots your historical portfolio value over time.
*   **ML Forecasting:** Toggle the Prophet forecasting model to display a shaded boundary predicting future portfolio values based on historical trends.

### 5. Deep Dive Allocation (`/analytics`)
Inspect where your money is actually distributed.
*   **Sector Allocations:** A colorful treemap showing the industries you are exposed to (e.g., Technology, Financials, Healthcare).
*   **Geographic Allocations:** Visual map of your country exposure (e.g., Australia, United States, Japan).
*   **Correlation Matrix:** A heatmap showing if your stocks move in tandem. If two stocks have a correlation of `1.0`, they move exactly together. A lower or negative correlation means they move independently, helping reduce portfolio risk.

### 6. Settings Page (`/settings`)
Tailor the dashboard's math and AI responses to your personal investment profile.
*   **Investment Goal:** Choose between Passive Income, High Growth, Balanced, Capital Preservation, or Tactical Trading.
*   **Risk Tolerance:** Set to Conservative, Moderate, or Aggressive.
*   **Tax Bracket:** Input your marginal tax rate to calculate accurate post-tax dividend projections and capital gains warnings.
*   **Dynamic Weight Previews:** View how your Goal and Risk selections adjust the mathematical weights used to score buying signals (Trend, Momentum, Value, Cost, Risk).

---

## 🤖 AI Assistant & Gemini Integration

Folio features a floating chatbot widget in the bottom-right corner of the screen, acting as your personal AI Research Assistant.

### AI Features:
*   **Portfolio-Aware Chat:** The chatbot knows what assets you own, your average cost basis, and your active strategy settings. You can ask: *"Are my tech stocks too risky for my Conservative profile?"* or *"Analyze my overall asset allocation."*
*   **Live Web Search Supplement:** If you ask about current market events (e.g. *"Why is BHP dropping today?"*), the assistant automatically enqueues a real-time DuckDuckGo News Search, reads the top results, and cites its sources.
*   **Weekly PDF Report:** Generate a professional multi-page report containing a holdings summary, upcoming ex-dividend calendars, technical indicators, news sentiment summaries, and AI-written market commentary.

### Gemini API Key Configuration
AI features require a Google Gemini API Key. 
1. Get a free key at [aistudio.google.com](https://aistudio.google.com).
2. Open the `.env` file in your root folder and add your key:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```
*Note: All core features—including price updates, charts, P&L history, analytics, dividends, and technical indicator scoring—work 100% offline without an API key.*

---

## 💻 Developer Reference & Directory Structure

If you wish to contribute to the code or understand the architecture, here is a guide to the codebase layout:

```
folio/
│
├── launcher.py                     # Core Process Manager (starts app.py and worker.py)
├── worker.py                       # Background Task Worker (prices, scraping, AI execution)
├── app.py                          # Dash App entry point (scaffolds stores & routing)
│
├── pages/                          # Page templates (HTML structure layouts)
│   ├── portfolio.py                # Dashboard Home
│   ├── positions.py                # Positions & Dividends deep-dive
│   ├── intelligence.py             # Risk ratios & forecasting UI
│   ├── etf_detail.py               # Detailed ETF underlying stock maps
│   └── settings.py                 # User profile settings
│
├── callbacks/                      # Presentation Layer (wires actions to UI)
│   ├── portfolio_callbacks.py      # Holdings table sorting, filtering, and render
│   ├── positions_callbacks.py      # Positions details & Candlestick triggers
│   ├── watchlist_callbacks.py      # Watchlist editing, notes, & drag-and-drop
│   ├── research_callbacks.py       # Chatbot context, limits, & PDF generation
│   ├── chart_callbacks.py          # Allocation treemaps & correlation heatmaps
│   └── ui_callbacks.py             # Theme switching, print, & refreshing
│
├── components/                     # Reusable UI Blocks & Charts
│   ├── header.py                   # Market status heartbeat & global nav
│   ├── watchlist_layout.py         # Watchlist structural widgets
│   ├── ui_helpers.py               # Theme containers & CSS grid wrappers
│   └── charts/                     # Plotly chart generators (pnl_history, candlesticks)
│
├── services/                       # Service Layer (Business logic & calculations)
│   ├── strategy_engine.py          # Quantitative BUY/SELL/HOLD scoring engine
│   ├── ai_engine.py                # Gemini critique overlays & verdict mapper
│   ├── research_service.py         # LLM chat coordination & DDG search integration
│   ├── intelligence_service.py     # Allocation compiling & risk mathematics
│   ├── prediction_service.py       # Facebook Prophet forecasting calculations
│   ├── report_service.py           # Matplotlib reports & ReportLab PDF compilation
│   └── market/                     # Market Service Layer
│       ├── data_fetcher.py         # Bulk Yahoo Finance downloads & calculations
│       ├── dividend_service.py     # Dividend schedules & ex-date mapping
│       ├── session_cache.py        # Intraday 5-min snapshot SQLite caches
│       └── market_status.py        # ASX session calendars & Sydney time checks
│
├── data/                           # Persistence Layer (SQLite Database access)
│   ├── database.py                 # SQLite WAL connection & schema initialization
│   ├── repository.py               # SQL transaction & holding queries
│   └── watchlist_repository.py     # SQL watchlist membership & notes queries
│
├── core/                           # Foundation Layer (Math helpers & Cache locks)
│   ├── engine/                     # Pure mathematical algorithms
│   │   ├── portfolio_engine.py     # Cost-basis tranches and P&L aggregations
│   │   └── stats_engine.py         # Formatter for UI values ($ and %)
│   ├── cache.py                    # Bounded memory cache with automatic eviction
│   └── validators.py               # Transaction inputs validation
│
├── assets/                         # CSS Overrides & Clientside Javascript
│   ├── base.css                    # Color theme variables & global resets
│   ├── layout.css                  # CSS Grid systems & responsive paddings
│   ├── drag_drop.js                # HTML5 event listeners for Watchlist drag-and-drop
│   ├── command_palette.js          # Search index & keyboard shortcut (Cmd+K)
│   └── browser_shutdown.js         # Graceful shutdown handler for page exits
│
└── scratch/                        # Diagnostic/Isolated Testing Suite
    ├── run_tests.sh                # Main automated test runner script
    └── tests/                      # 9 mock-isolated unit testing suites
```

### Decoupling Rules
- **Services Purity:** Files inside `services/` represent pure business logic and computations. They must never import from Dash libraries, layouts, or pages.
- **Engine Isolation:** Files inside `core/engine/` contain pure mathematical algorithms (zero network calls, zero file I/O, zero database queries). This makes testing robust and predictable.
- **Minimal Edits:** If editing code, focus edits on the specific function. Never modify protected scaffolding files (like `app.py` store seeds or `data/database.py` WAL config) without explicit design documentation.

---

## 🧪 Testing

Folio maintains a high-coverage unit testing suite built on `pytest`. All tests are fully mock-isolated, meaning they run without making network requests to Yahoo Finance or writing to your production database file.

To run the automated tests:
```bash
# Run all unit tests and generate coverage metrics
./scratch/run_tests.sh

# Open the visual coverage dashboard in your browser
open htmlcov/index.html
```

---

## 📊 Technical Stack Reference

| Component | Library / Engine |
| :--- | :--- |
| **User Interface** | Dash, Dash Mantine Components, Dash Bootstrap Components, Plotly |
| **Database** | SQLite (WAL mode enabled, thread-safe concurrent writes) |
| **Market Data** | yfinance (bulk-optimized downloads with intraday session cache) |
| **Technical Indicators** | Pure Pandas calculations (Wilder's RSI, MACD, Bollinger Bands) |
| **Forecasting** | Facebook Prophet (incorporates Sydney trading holidays) |
| **AI Models** | Google Gemini 2.5 Flash Lite (`google-genai` SDK) |
| **PDF Compilation** | ReportLab & Matplotlib |
| **Search Discovery** | DuckDuckGo Search (`ddgs` indexer API) |

---

## ⚖️ Disclaimer

Folio started as a personal tracker to solve ASX portfolio management limitations. Approximately 80% of this codebase was generated using AI tools. You should expect occasional minor bugs and are encouraged to double-check critical calculations against your broker statements.

Nothing calculated or displayed by Folio constitutes financial advice. Always consult a licensed financial advisor before making investment decisions.

---

## 📜 License

MIT License © 2026 Vishal Manoj Kumar
