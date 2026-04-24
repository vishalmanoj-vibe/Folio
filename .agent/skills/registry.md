# Skill: Component ID Registry

## Objective
Prevent "Duplicate ID" errors and callback collisions by maintaining a central map of all critical Dash component IDs.

## Global Stores (Always Present)
- `portfolio-store`: Main holdings and current prices.
- `txn-store`: Full transaction history.
- `theme-store`: Light/Dark mode state.
- `url`: Location tracking for multi-page routing.

## Page-Specific IDs

### Overview / Portfolio
- `stat-cards`: Main KPI summary cards.
- `pnl-history-chart`: Core equity curve.
- `pnl-mode`: Percentage/Dollar toggle.
- `portfolio-treemap`: Asset allocation view.
- `live-table`: Main holdings table.

### Analytics & Intelligence
- `intel-risk-cards`: Volatility, Sharpe, Drawdown stats.
- `intel-equity-chart`: Historical performance comparison.
- `intel-drawdown-chart`: Peak-to-trough analysis.
- `intel-period-picker`: 1m, 3m, 6m, 1y, YTD, All.
- `intel-alerts`: Risk and opportunity notifications.

### Dividends
- `dividend-stats-cards`: Projected income and yield KPIs.
- `dividend-yield-chart`: Historical yield tracking.
- `dividend-growth-chart`: Annual income progression.
- `dividend-table`: Upcoming and past payment log.

### Positions & Transactions
- `positions-card-grid`: Ticker-based selection cards.
- `positions-price-chart`: Individual stock performance.
- `positions-txn-table`: Filtered transaction history for selection.
- `txn-submit`: Button for "Add Transaction" form.

## Rule for New IDs
- **Namespace Pattern**: Always prefix new IDs with the page name (e.g., `tax-report-table`).
- **Update this file**: Whenever a new ID is added, it MUST be registered here.
