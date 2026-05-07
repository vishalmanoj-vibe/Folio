# Skill: Component ID Registry

## Objective
Prevent "Duplicate ID" errors and callback collisions by maintaining a central map of all critical Dash component IDs.

<!-- FIX: Pruned 2 orphaned IDs (dividend-growth-chart, watchlist-table). Added 40+ active IDs missing from previous version. Last synced: 2026-04-26. -->

## Global Stores & Singletons (Always Present — Seeded in app.py)
- `url`: Location tracking for multi-page routing.
- `live-interval`: 30-second refresh ticker.
- `txn-store`: Full transaction history.
- `portfolio-store`: Main holdings, prices, and price histories.
- `watchlist-store`: Global store for watchlist market data.
- `alerts-store`: Active alert list.
- `signals-store`: Rule-based + AI trading signals (session storage). Structure: `{"raw": {...}, "ai": {...}}`. Populated only on manual trigger.
- `theme-store`: Light/Dark mode state (local storage).
- `compact-mode-store`: Compact UI toggle state (local storage).
- `table-state-store`: Holdings table sort column + direction (local storage).
- `nav-link-store`: Active nav link tracking.

## Session Picker Stores (Persist across pages in same session)
- `period-store`: P&L chart period selection.
- `pnl-mode-store`: P&L mode (pct / dollar).
- `ticker-store`: Selected ticker for P&L chart.
- `treemap-mode-store`: Treemap grouping mode (sector / geo).
- `analytics-period-store`: Analytics page period selection.
- `intel-period-store`: Intelligence page period selection.
- `intel-pred-store`: Intelligence forecast toggle state.
- `positions-selected-ticker`: Currently selected position card.
- `positions-period-store`: Positions chart period selection.
- `watchlist-selected-ticker`: Currently selected watchlist card.
- `watchlist-period-store`: Watchlist chart period selection.
- `research-chat-store`: Conversation history (memory — clears on refresh).
- `research-ticker-store`: Ticker being researched (memory — clears on refresh).
- `research-usage-store`: AI request count + reset date (local storage).

## Page-Specific IDs

### Header / Global Controls
- `market-status`: Live market open/closed badge.
- `last-updated`: Timestamp of most recent data refresh.
- `refresh-btn`: Manual refresh button.
- `theme-toggle`: Light/Dark mode toggle button.
- `theme-icon-indicator`: Icon inside the theme toggle.
- `settings-icon-text`: Gear icon text in header.
- `compact-toggle-btn`: Compact mode toggle button.
- `pdf-btn`: Export/print button.
- `alerts-banner`: Global alert message strip above content.
- `intel-alert-count`: Badge on intelligence nav link showing alert count.

### Overview / Portfolio Page (`/`)
- `stat-cards`: Main KPI summary cards row.
- `pnl-history-chart`: Core equity P&L curve.
- `pnl-mode`: Percentage/Dollar toggle segmented control.
- `period-picker`: P&L chart period segmented control.
- `ticker-selector`: Ticker dropdown for P&L chart overlay.
- `portfolio-treemap`: Asset allocation treemap.
- `treemap-mode`: Treemap grouping mode control.
- `live-table`: Main holdings table. Includes columns for Ticker, Name, Shares, Avg cost, Last price, Day change, High/Low, Market value, Cost basis, P&L, Suggestion, and Yield.
- `table-filter`: Holdings table search/filter input.

### Transactions (embedded on Portfolio page)
- `txn-type`: Transaction type selector (buy/sell).
- `txn-ticker`: Ticker text input.
- `txn-shares`: Number of shares input.
- `txn-price`: Price per share input.
- `txn-date`: Transaction date picker.
- `txn-submit`: Submit button for Add Transaction form.
- `txn-msg`: Status/feedback message text.
- `txn-ticker-hint`: Auto-discovered ticker name hint.
- `txn-log`: Rendered transaction history table.
- `txn-collapse`: Collapse toggle for transaction form.
- `txn-history-details`: Expandable transaction detail block.

### Analytics Page (`/analytics`)
- `price-chart`: Normalised price history chart.
- `analytics-period-picker`: Analytics period segmented control.
- `analytics-vol-chart`: Annualised volatility bar chart.
- `corr-chart`: Correlation heatmap.

### Intelligence Page (`/intelligence`)
- `intel-risk-cards`: Volatility, Sharpe, Max DD, Current DD stat cards.
- `intel-equity-chart`: Historical portfolio equity curve.
- `intel-drawdown-chart`: Peak-to-trough drawdown chart.
- `intel-period-picker`: 1m, 3m, 6m, 1y, YTD, All picker.
- `intel-pred-toggle`: Forecast on/off switch.
- `intel-forecast-label`: Text label next to forecast toggle.
- `intel-alerts`: Smart alert cards block.
- `intel-data-note`: Data source annotation strip.
- `intel-signals-table`: Technical indicator signals table (RSI, MACD, Bollinger Bands).

### Dividends Page (`/dividends`)
- `dividend-stats-cards`: Annual income, yield, realized total KPI cards.
- `dividend-calendar`: Upcoming payment calendar card grid.
- `dividend-income-chart`: Annual income by holding progress rows.
- `dividend-yield-chart`: Yield by holding progress rows.
- `dividend-table`: Full ex-date / pay-date dividend log table.

### Positions Page (`/positions`)
- `positions-card-grid`: Ticker card selection grid.
- `positions-selected-ticker`: Store — currently active card.
- `positions-detail-title`: Detail panel section heading.
- `etf-detail-cards`: Metrics card grid for selected holding.
- `etf-detail-panel`: Wrapper for the full detail panel.
- `positions-price-chart`: Candlestick price chart for selected holding.
- `positions-period-btns`: Period button row for price chart.
- `positions-period-store`: Store — current period selection.
- `positions-txn-table`: Transaction history table for selected holding.
- `generate-signals-btn`: "Generate Signals" button — triggers `signals_callbacks.generate_signals_callback`.
- `loading-signals`: `dcc.Loading` wrapper around the status label (NOT the button — wraps the Output target).
- `signals-status-label`: Status span inside `loading-signals`; shows "Updated HH:MM" or error text after signal run.

### Watchlist Page (`/watchlist`)
- `watchlist-input`: Ticker text input for adding new watchlist item.
- `watchlist-add-btn`: "Add to Watchlist" submit button.
- `watchlist-store`: Global store for watchlist market data.
- `watchlist-selected-ticker`: Store — currently selected watchlist ticker.
- `watchlist-table-container`: Container div for the full watchlist table.
- `watchlist-msg`: Status/error message paragraph.
- `watchlist-chart`: Price history line chart for selected watchlist ticker.
- `watchlist-chart-title`: Title text for the watchlist chart.
- `watchlist-stat-cards`: Grid of 4 stat cards for selected watchlist ticker (+ optional AI card).
- `watchlist-notes-input`: Textarea for per-ticker research notes.
- `watchlist-notes-save-btn`: Save button for research notes.
- `watchlist-notes-msg`: Status span for save confirmation.
- `watchlist-signals-store`: Rule-based + AI signals for watchlist tickers (session). Structure: `{"raw": {...}, "ai": {...}}`. Populated only on manual trigger.
- `watchlist-generate-signals-btn`: "Generate Signals" button — triggers `generate_watchlist_signals_callback`.
- `watchlist-loading-signals`: `dcc.Loading` wrapper around the watchlist status label.
- `watchlist-signals-status-label`: Status span showing "Updated HH:MM" or error text after signal run.
- `wl-period-btn-row`: Watchlist chart period button row.

### Research Assistant Page (`/research`)
- `research-portfolio-summary`: Left panel live holdings display.
- `research-chat-display`: Scrollable chat message area.
- `research-ticker-input`: Free-text ticker to research.
- `research-input`: Chat message text input.
- `research-send-btn`: Message send button.
- `research-send-btn-wrapper`: Wrapper div for send button (loading state).
- `research-disclaimer`: Static disclaimer text element.
- `research-typing-indicator`: Animated typing indicator strip.
- `research-usage-display`: AI request usage counter display.
- `qp-1`: Quick prompt chip — "Does this fit my portfolio?"
- `qp-2`: Quick prompt chip — "What are the risks?"
- `qp-3`: Quick prompt chip — "Compare to what I own"
- `qp-4`: Quick prompt chip — "What am I missing?"

### Reports Page (`/reports`)
- `generate-report-btn`: Main "Generate Weekly Report" button.
- `report-status-msg`: Status message / feedback text area.
- `report-download-area`: Wrapper for the ready download link (hidden until ready).
- `report-pdf-link`: Link to open/download the base64 encoded PDF.
- `last-report-date`: Text showing when the last report was generated.
- `report-download`: dcc.Download component for file exports.
- `report-cache-store`: dcc.Store for session-based report caching.

## Pattern-Matched IDs (Dynamic — do not hardcode)
- `{"type": "pos-card", "index": <ticker>}`: Holding selection cards on Positions page.
- `{"type": "pos-period-btn", "index": <period>}`: Period buttons on Positions page.
- `{"type": "table-th", "index": <col_id>}`: Sortable column headers on holdings table.

## Rules for New IDs
- **Namespace Pattern**: Always prefix new IDs with the page name (e.g., `tax-report-table`).
- **Update this file**: Whenever a new ID is added, it MUST be registered here.
- **Conflict check**: Before building any new feature, grep the existing IDs in
  this file to confirm no collision. Never reuse an ID from another page.
- **research-* namespace**: Reserved for the Research Assistant page. Do not
  use this prefix for any other feature.
