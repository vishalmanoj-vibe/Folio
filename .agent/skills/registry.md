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
- `live-table`: Main holdings table.
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

### Watchlist Page (`/watchlist`)
- `watchlist-input`: Ticker text input for adding new watchlist item.
- `watchlist-add-btn`: Add ticker to watchlist button.
- `watchlist-msg`: Status/feedback message text.
- `watchlist-table-container`: Rendered watchlist items table.
- `watchlist-stat-cards`: Market data stat cards for selected ticker.
- `watchlist-chart`: Selected ticker price history chart.
- `watchlist-chart-title`: Dynamic title for the watchlist chart.
- `watchlist-notes-input`: Freeform notes textarea for selected ticker.
- `watchlist-notes-save-btn`: Save notes button.
- `watchlist-notes-msg`: Notes save status message.
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
