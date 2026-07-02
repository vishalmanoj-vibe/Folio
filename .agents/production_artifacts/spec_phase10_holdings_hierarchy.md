# Technical Spec: Restructure ETF Underlying Holdings & URL Config Sync

## Feature Summary
Restructure the "Underlying Holdings" mode in the treemap to render hierarchically by grouping companies under their parent ETF tickers instead of flat merging. Additionally, display all tickers present in the transactions/portfolio inside the "Configure Sources" URL table, allowing users to verify auto-discovered links or configure custom URLs for newly added ETFs like URNM.

## Modified Files
- `components/charts/treemap.py`
- `callbacks/chart_callbacks.py`
- `services/market/holdings_fetcher.py`

## Component IDs
No new Dash Component IDs are introduced.

## Data Strategy
- Uses `fetch_holdings` on each portfolio ticker in the `portfolio_treemap` callback.
- Accesses `portfolio-store` as State in `load_url_table` to retrieve currently held tickers.
- Persists user-defined URLs and auto-discovered URLs in the `etf_holdings_urls` database table.
- Added `URNM` with official BetaShares page to `PROVIDER_SEED_URLS` default dictionary.

## Resolved Pain Points
- **Duplicate ID Collisions**: Company leaf nodes are identified uniquely as `f"{ticker}_{company}"` so that the same stock (e.g. NVIDIA) can be rendered under multiple parent ETFs without causing Plotly rendering conflicts.
- **Ambiguous "Other" Nodes**: Flat merging created multiple duplicate "Other" categories. Nesting groups them under their respective parent ETF as `f"{ticker}_Other"` (labelled "Other").
- **Missing Tickers in URL Config**: Syncs all portfolio tickers so newly added assets like URNM automatically appear in the URL table for user visibility and custom updates.
- **Broken URL Links**: Displays `"—"` as unclickable text instead of generating a broken hyperlink if no seed/user URL is configured.
- **Auto-Discovery URL Cache**: Saves DDGS-discovered URLs directly to SQLite, avoiding repetitive 5-second search lookups during subsequent refreshes.

## Related Files
- **Skills:** [Add Chart](../skills/add_chart.md), [Data Fetching & Scrapers](../skills/data_fetching.md), [Component ID Registry](../skills/registry.md)
- **Reference:** [Known Issues](../../docs/reference/known_issues.md)
- **Code:** [treemap.py](../../components/charts/treemap.py), [holdings_fetcher.py](../../services/market/holdings_fetcher.py)
