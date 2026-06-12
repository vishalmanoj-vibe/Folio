# Build Log: Correlation Matrix Reactivity & Color Scale Fix

This build fixes the period-picker reactivity bug for the Correlation Matrix and Volatility list on the Deep Dive page, and improves the heatmap colorscale to be more financially intuitive.

## Changed Files
- **[callbacks/chart_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/chart_callbacks.py)**: Changed `analytics-period-store` dependency from `State` to `Input` in both `update_corr_chart` and `update_analytics_volatility` callbacks to enable reactivity on period filter selection.
- **[components/charts/correlation.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/charts/correlation.py)**: Updated the Plotly marker `colorscale` to color low-correlation pairs (`≤ 0.2`) green/teal for clear diversification visibility.
- **[data/cache_manager.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/data/cache_manager.py)**: Fixed minor SQL syntax trailing whitespaces.
- **[scratch/tests/test_chart_components.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scratch/tests/test_chart_components.py)**: Appended `test_build_corr_figure` unit test to cover normal rendering, empty fallback states, and the custom colorscale.

## Verifications Passed
- Python ruff check passed successfully.
- Pytest suite executed via `scratch/run_tests.sh`: all **182 unit tests passed successfully**!
