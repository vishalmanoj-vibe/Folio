# Build Log: Underlying Holdings Integration in Allocation Treemap

This build successfully integrates underlying ETF holdings data directly into the Allocation Treemap under the new "Underlying Holdings" filter option, removing the separate ETF Holdings tab and its bubble chart.

## Changed Files
- **[pages/analytics.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/analytics.py)**: Removed "ETF Holdings" tab header and tab panel, added "Underlying Holdings" filter option to the segmented control, and moved the freshness note directly below the treemap canvas description.
- **[components/charts/treemap.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/charts/treemap.py)**: Added `holdings_data` support to `build_portfolio_treemap()`. Implemented calculations to group smaller exposures into "Other Underlying", computed absolute market values, and formatted hover tooltips listing source ETFs.
- **[callbacks/chart_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/chart_callbacks.py)**: Removed the `update_holdings_bubble_chart` callback and its imports. Updated the `portfolio_treemap` callback to accept multi-output parameters for the figure, freshness note, and sources collapse state.
- **[scratch/tests/test_chart_components.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scratch/tests/test_chart_components.py)**: Replaced `test_build_holdings_bubble_chart` with `test_build_portfolio_treemap_holdings` to test underlying holdings nodes, dollar sizing, and fallback behavior.
- **[docs/callback_ownership.md](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/docs/callback_ownership.md)**: Updated output mappings for `portfolio-treemap`, `holdings-freshness-note`, and `holdings-url-collapse` to reflect the updated callback definitions.

## Removed Files
- None.

## Component IDs & Properties Updated
- `treemap-mode` (data options updated)
- `portfolio-treemap` (figure output)
- `holdings-freshness-note` (children output relocation)
- `holdings-url-collapse` (opened output with allow_duplicate=True)

## Verifications Passed
- Pytest suite passes: 61/61 tests pass.
- Browser subagent checklist completed successfully, capturing visual proof of correct rendering.
