# Core Algorithms & Special Features

> Back to [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

This guide documents the specific mathematical formulas, core algorithms, and specialized logic layers of the Folio portfolio dashboard.

---

## Core Algorithms & Special Logic

### 1. Realized Dividend Engine
Unlike standard dashboards that only show current yield, this app computes **Realized Dividends** by correlating distribution history with purchase tranches.
- **Tranche Matching**: A dividend is only credited if `purchase_date < ex_dividend_date`.
- **Accuracy**: This prevents "phantom income" from showing up for stocks bought after their ex-date.

### 2. Prophet Forecasting & Continuity Correction
The forecasting engine in `prediction_service.py` uses Facebook Prophet with a custom "Continuity Correction" layer.
- **The Problem**: Trends fitted by Prophet often have a vertical gap between the last historical price and the first forecasted point.
- **The Fix**: We calculate the `drift` (Actual Last - Fitted Last) and apply it as a vertical offset to the entire forecast series, ensuring a smooth visual transition.

### 3. Advanced Risk Metrics
Metrics in `intelligence_service.py` are calculated using standard financial formulas:
- **Sharpe Ratio**: `(Mean Excess Return / Std Dev of Return) * sqrt(252)`, using a 4.35% (Current RBA/Fed-proxy) risk-free rate.
- **Volatility**: Annualized standard deviation of daily log returns.
- **Drawdown**: Percentage drop from the previous all-time high in the selected period.

### 4. Parallel Market Fetching & Caching
To ensure high performance with multi-ticker portfolios, the `fetch_live` service utilizes concurrency:
- **Parallel Workers**: Uses `ThreadPoolExecutor` (10 workers) to parallelize sequential I/O-bound requests (e.g., `ticker.info` for names and dividends).
- **Metadata Caching**: Implements a simple in-memory TTL cache for Yahoo Finance metadata, avoiding redundant network calls for static data (ETF names, payout frequencies).
- **Domain-Specific TTLs**: Separates heavy computations from the 300s live tick. Technical signals are cached for 24 hours (`TECHNICALS_CACHE_TTL`), and historical dividend processing is cached for 7 days (`DIVIDENDS_CACHE_TTL`).
- **Bulk Downloads**: Continues to use `yf.download()` for primary price history to minimize HTTP overhead.

## Styling & UI Architecture

### CSS Token System
The application uses a strictly themed design system defined in `assets/base-tokens.css`. Developers must use these variables instead of hardcoded hex values to ensure theme consistency.

| Category | Tokens | Purpose |
|----------|--------|---------|
| **Theme** | `--bg`, `--surface`, `--surface-2` | Base layers & card backgrounds |
| **Type** | `--t-pri`, `--t-sec`, `--t-muted` | Hierarchical typography colors |
| **Brand** | `--cyan`, `--cyan-2` | Primary accents & active states |
| **Status** | `--green`, `--red`, `--warning` | Semantic feedback (P&L, Alerts) |
| **Lines** | `--border`, `--border-2` | Section dividers & accent borders |

### CSS Modularization & Loading
1.  **`base-tokens.css`**: Defines CSS variables.
2.  **`base-reset.css`**: Global resets and base typography.
3.  **`ui-components.css`**: Shared component blocks.
4.  **`layout.css`**: Structural layout, navigation, and glassmorphism.
5.  **`vendor.css`**: High-specificity overrides for Radix/Dash components.

### Premium UI Standards
To maintain a "Linear-inspired" aesthetic, the dashboard implements several high-end UI patterns:
- **Glassmorphism**: The navigation bar utilizes `backdrop-filter: blur(12px)` and semi-transparent backgrounds (`var(--nav-bg)`) to create a frosted-glass effect.
- **Smooth Transitions**: All theme-aware layout shifts use a `0.2s ease` transition duration for background and border colors.
- **Interactive Depth**: Dashboard cards and stat containers implement a `translateY(-2px)` lift on hover, combined with a subtle teal glow (`var(--glow)`) to provide tactile feedback.
- **Data Vitality**: A real-time pulse indicator in the header provides at-a-glance evidence of live market monitoring, with a CSS-animated "heartbeat" synchronized with the ASX trading session.

### Chart Standardization (`apply_standard_layout`)
All Plotly visualizations must be routed through the `apply_standard_layout()` helper in `components/charts/helpers.py`. This ensures:
- **Typography**: Unified **Inter 10px** styling for all axes, legends, and annotations.
- **Grid Consistency**: Standardized grid line opacities and subtle border treatments across all pages.
- **Hover UX**: Enforced `hovermode="x unified"` for professional, multi-trace data inspection.
- **Theme Awareness**: Dynamic mapping of axis and tick colors to current design tokens (`var(--t-sec)`).

### Overriding Dash 2.16+ (Radix UI)
Modern Dash components often render elements in "Portals" at the end of the document body. 
- Use **Wildcard Attribute Selectors** (e.g., `div[class*="dash-datepicker"]`).
- Aggressive use of `!important` within the `vendor.css` layer is sanctioned for these overrides to ensure theme consistency across portal boundaries.

### Transaction Flow Migration
The transaction entry system was migrated from a standard `dcc.Input` to a Mantine `dmc.DateInput` for a more polished UI.
- **Component**: `dmc.DateInput` in `components/portfolio_layout.py`.
- **State Change**: In `callbacks/transaction_callbacks.py`, the callback now listens to the `value` property (ISO YYYY-MM-DD string).
- **Validation**: The `validate_transaction` service remains compatible as it expects the same ISO format.

---

## Specialized Features

### 1. Insights & Risk Analysis
The **Insights Page** provides a deep dive into portfolio risk.
- **Metrics**: Annualized Volatility, Sharpe Ratio, and Max Drawdown are calculated using pure Python in `intelligence_service.py`. 
- **Optimization**: To avoid double-calculating heavy return series (e.g. when forecasting is enabled), returns are pre-computed once and passed into the metrics engine.
- **Robustness**: Safety checks ensure that missing ETF metadata (`funds_data`) doesn't crash the engine; it falls back to parsing the `info` category or symbol-based inference.
- **Treemap Charts**: Hierarchical allocation (Sector/Geography) is rendered using `Plotly Treemap` traces for high-density space efficiency.
- **Drill-down**: Clicking a sector/region in the Treemap triggers a modal displaying the exact ticker-level contribution.
- **Smart Alerts**: A rule-based engine evaluates the portfolio against `THRESHOLDS` (e.g., >40% in one sector) to generate actionable insights.

### 2. Portfolio Forecasting (Prophet)
Forward-looking projections are handled by `prediction_service.py`.
- **Model**: Uses Facebook Prophet with Australian holiday awareness.
- **Tiered Caching**: To ensure UI responsiveness, forecasts are computed once and stored in `data/cache/predictions.json` (disk cache) and also held in the `dcc.Store` (client cache).
- **Confidence Intervals**: Displays an 80% uncertainty band to highlight potential market volatility.

### 3. Realized Dividend Tracking
Unlike standard yield calculations, the app computes **Realized Dividends** by matching historical Ex-Dividend dates against the user's specific holding tranches. 
- **Logic**: A dividend is "realized" only if the tranche purchase date is strictly before the Ex-Dividend date.
- **Accuracy**: This provides a dollar-accurate representation of income actually earned, rather than a theoretical annual yield based on current price.
- **Visualization**: The dashboard displays both ticker-specific dividend trends and global portfolio dividend history directly on the Positions page, providing a consolidated view of income.

### 4. Intraday Market Sessions (Today View)
The "Today" P&L view utilizes a dedicated intraday tracking system to provide real-time updates without the limitations of standard daily-interval data.
- **Data Source**: Every time the dashboard refreshes (default 300s), the current state is appended to a local JSON snapshot (`data/cache/intraday_YYYY-MM-DD.json`).
- **Bypass Strategy**: The P&L History chart reads this file directly when in "1d" mode. This bypasses the main `portfolio-store` for chart rendering, preventing "Timezone Concat" errors that occur when mixing historical daily data (often UTC-naive) with live intraday data (Sydney wall-clock).
- **Window**: The chart is strictly pinned to the ASX trading window (10:00 AM – 4:15 PM Sydney Time).
- **Persistence**: Snapshotting ensures that intraday progress is preserved even if the application is restarted during the trading day.

### 5. Technical Indicators Engine (Pure Pandas)
The **Technical Indicators Service** (`services/technical_indicators.py`) provides high-performance technical analysis without external TA library dependencies.
- **Pure Pandas Math**: All indicators (RSI, MACD, Bollinger Bands) are implemented using native pandas vectorized operations (`ewm`, `rolling`, `std`) to ensure portability and speed.
- **Wilder's Smoothing**: The RSI implementation uses Wilder's method (`com=period-1`) to match industry-standard trading platforms.
- **Standardized Signals**: The `compute_signals` function returns a consistent 10-key dictionary, including human-readable labels (e.g., "Oversold", "Bullish") for immediate UI consumption.

### 6. OHLC Data Architecture & Candlestick Support
The data fetching layer was enriched to support high-fidelity price visualization.
- **OHLC Extraction**: The `data_fetcher.py` now extracts `Open`, `High`, and `Low` columns in addition to `Close`. 
- **Graceful Fallback**: Since the "1d" (intraday) period often lacks OHLC columns, the system implements a fallback to standard Line charts (`go.Scatter`) when Candlestick data is unavailable.
- **Data Cleansing**: The fetcher performs a strict `dropna(subset=["Close"])` and timezone normalization on combined OHLC frames to prevent rendering crashes.

### 7. Multi-Page Period Synchronization
To ensure consistent data views across the dashboard, the application implements a "Global Max Period" strategy.
- **The Problem**: Different pages (e.g., Positions vs. Watchlist) may request different time periods, but they share the global `portfolio-store`.
- **The Fix**: The refresh callback in `app.py` evaluates all active page-specific period stores and instructs the market service to fetch the **maximum** duration requested. This ensures that when a user switches pages, the required historical data is already present in the global cache.

### 8. Floating AI Assistant Widget & Persistent Memory
The **Floating AI Chatbot Widget** (defined in `components/chatbot.py`) leverages Google Gemini 2.5 Flash (guided by your Investor Profile settings) for contextual portfolio reasoning.
- **Contextual Awareness**: On every query, the assistant is injected with active path/ticker context, including a live snapshot of the portfolio (Holdings, P&L, Weights) and the active ticker.
- **Technical Integration**: Live technical signals (RSI/MACD/BB) are automatically computed and injected into the prompt context, allowing the AI to reason about technical entry points.
- **Cost & Performance Optimization**:
    - **Deterministic Caching**: To minimize Gemini API costs, the `ai_engine.py` generates a cache key based on a stable subset of signals (Signal + Rounded Score). Highly volatile live price ticks are ignored for cache key generation.
    - **SDK Compatibility**: The engine uses the `google.genai` SDK with standardized parameter sets to ensure reliability and 10s-range response times.
- **Rolling Memory Pattern**: To provide continuity without bloating storage, the system uses a dual-layer memory:
    - **Short-Term (7-day Log)**: Exact conversation turns stored in `conversation_log.json`.
    - **Long-Term (AI Summary)**: On startup, old turns are automatically summarized into bullet points by Gemini and saved to `memory_summary.json`.
- **Usage Monitoring**: A daily message limit (20) and storage cap (50MB) are enforced.
- **Startup Maintenance**: The `run_startup_maintenance` routine in `app.py` ensures the memory remains pruned and summarized before the app accepts user input.

### 9. Live Web Search Integration
The research assistant is now equipped with real-time web search capabilities to supplement portfolio context.
- **Trigger**: The `should_search_web` function evaluates user messages for financial keywords (e.g., "announcement", "forecast", "asx").
- **Smart Querying**: If a search is triggered, the system constructs a targeted query combining the user message with the active ticker context.
- **Provider**: Powered by `duckduckgo-search` (via the `ddgs` package), fetching the most recent (last month) Australian financial news.
- **UI Feedback**: Assistant responses that incorporate web data are clearly marked with a `🔍 Web search used` indicator.

### 10. Technical Charting & UI Layout Stability
To provide a professional trading experience, the dashboard implements several layout and visualization safeguards:
- **Layout Isolation (AI Insights)**: To prevent large blocks of AI-generated text from disrupting the CSS Grid, Assistant insights are rendered in a dedicated `ai-insight-container`. This prevents the "auto-fit" behavior from shrinking the top-level metric cards when the AI card expands.
- **Dynamic Chart Scaling**: Price charts on the Watchlist page calculate the period's min/max prices dynamically. The Y-axis is constrained to `[min * 0.98, max * 1.02]`, eliminating the massive empty gap at the bottom of the chart.
- **Typography Standards**: All AI-generated explanations use standard 13px body font sizes with 1.5 line height for readability, while technical metrics (e.g., RSI Score) are consistently themed using the primary accent color (`var(--cyan)`).

### 11. UI Layout Standardization (Grid & Sectioning)
To eliminate visual inconsistencies and "compactness" issues, the dashboard follows a strict 24px horizontal grid.
- **Header Standard**: `.page-header-row` is fixed at `padding: 16px 24px`.
- **Structural Wrappers**: All major content blocks must be wrapped in the `section()` helper from `components.ui_helpers`. This enforces a `0.5px` bottom border and a uniform `16px 24px` padding.
- **Dynamic Rendering**: To prevent "empty dashboard syndrome", pages use dynamic containers (e.g., `positions-price-chart-container`) that hide headers and empty plots until a ticker is selected, ensuring the initial state is clean and professional.

### 12. Deterministic Strategy Engine & AI Critique
The dashboard includes a hybrid decision-support system:
- **Strategy Engine** (`services/strategy_engine.py`): Pure, rule-based logic that generates BUY/SELL/HOLD signals based on five weighted dimensions (Trend, Momentum, Price vs 200MA, Price vs Cost, and Risk).
- **Assistant Overlay** (`services/ai_engine.py`): Gemini critiques the deterministic signals, providing human-readable context and risk flags without overriding the engine's verdict.
- **Hysteresis**: To prevent signal flickering on volatile days, the engine implements a "flip-prevention" logic where a signal change is only accepted if the new score exceeds a 0.7 confidence threshold.
- **Overview Integration**: Signals from the engine are automatically injected into the main Holdings Overview table as a "Suggestion" badge.

### 13. Intraday Resampling & Resiliency
To ensure the "Today" P&L chart remains professional and readable:
- **5-Minute Resampling**: Live data is resampled to 5-minute intervals (`resample('5min').last().ffill()`).
- **Trading Session Stitching**: Plotly `rangebreaks` are applied to the X-axis to hide overnight sessions and weekends.
- **Background Snapshotting**: A dedicated thread in `app.py` records market snapshots every 5 minutes while the market is open.

### 14. Deep Dive Visualization & Theme Integration
To provide a seamless visual experience, the Allocation and Performance charts in the Deep Dive page are deeply integrated with the design system.
- **Background Harmonization**: All Plotly figures utilize `paper_bgcolor="rgba(0,0,0,0)"` and `plot_bgcolor="rgba(0,0,0,0)"`, ensuring they blend perfectly with the CSS `var(--surface)` layer.
- **Theme-Aware Typography**: Labels and titles are dynamically mapped to CSS variables (e.g., `var(--t-pri)`), ensuring high contrast and readability.
- **Template Stripping**: Standard Plotly templates are disabled.

### 15. Standardized Architecture Compliance
Following a project-wide audit, the application adheres to strict operational standards:
- **Logging Purity**: All `print()` statements in the service and data layers have been replaced with `logger.debug()` or `logger.info()`.
- **Callback Safety**: Multi-page safety requires that page-specific rendering callbacks use `prevent_initial_call=False` (or `"initial_duplicate"`), while interaction callbacks (e.g. form submission, clicks) use `prevent_initial_call=True`.

### 16. Callback Prioritization & Rendering Efficiency
To maintain 60FPS UI responsiveness even when global stores update frequently, the dashboard implements **URL-Aware Prioritization**:
- **Guard Clause**: Every page-specific rendering callback includes `Input("url", "pathname")`.
- **Logic**: If the current `pathname` does not match the callback's page, it returns `dash.no_update` immediately.

### 17. Standardized Chart Fallbacks
To prevent the appearance of broken "empty grid" charts during data loading or error states:
- **Centralized Helper**: All charts must use `create_empty_fig()` from `components.charts.helpers`.

### 18. UI Aesthetics & Live Tracking
To create a premium, "live" feel similar to modern fintech applications, the dashboard implements smooth value transitions:
- **CSS Transitions**: Major numeric values (Portfolio P&L, Card Metrics, Summary Strips) utilize `transition: all 0.3s ease`.

### 19. Loading Experience (Skeletons & uirevision)
To ensure a professional "Day 1" experience and prevent UI flicker during updates:
- **Fixed-Column Skeletons**: To prevent layout shift (vertical stacking) during loading, `custom_spinner` containers utilize fixed-column grids (e.g., `repeat(6, 1fr)`) with explicit `width: 100%`.
- **Stable Charts (uirevision)**: All major Plotly figures implement `uirevision=True`.
- **Skeleton Helpers**: Standard placeholders are available in `components/ui_helpers.py` (`stat_card_skeleton`, `chart_skeleton`, `table_skeleton`).

### 20. Manual Watchlist Drag-and-Drop Reordering
To provide a premium and interactive fintech feel, users can manually click-and-drag rows in the **Market Watchlist** to reorder their watched assets.
- **Visual Drag Handles**: Leftmost column displays grab handles (`☰`) that change cursor to `grab` on active hold.
- **Event Delegation Engine**: A custom JavaScript asset `assets/drag_drop.js` attaches listeners to the document body, surviving complete DOM refreshes.
- **Mousedown Click-Source Tracking**: Restricts drag sequences exclusively to clicking the `.drag-handle` element.
- **State Synchronization Bridge**: Dropped rows update `dcc.Input(id="watchlist-order-input")` which notifies Python callbacks.
- **Relational Persistence**: `update_watchlist_store` invokes `repo.update_watchlist_order()` to write new indexes to SQLite.
