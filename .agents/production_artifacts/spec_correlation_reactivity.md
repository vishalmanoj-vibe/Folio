# Spec: Correlation Matrix Reactivity & Color Scale Fix

## Feature Summary
This change fixes the correlation matrix and volatility list on the Deep Dive (`/analytics`) page. Currently, these components do not update when the user changes the period picker because their callbacks listen to the period store as `State` instead of `Input`. We will also update the colorscale of the correlation heatmap so that low correlations (e.g. `≤ 0.2`) are colored green instead of orange/yellow, aligning with financial diversification intuition.

## Proposed Changes

### Component Callbacks

#### [MODIFY] [chart_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/chart_callbacks.py)
Change `State("analytics-period-store", "data")` to `Input("analytics-period-store", "data")` in both:
- `update_corr_chart` (line 394)
- `update_analytics_volatility` (line 324)

This will trigger updates for the correlation matrix and volatility progress bars whenever the period selector is changed.

### Chart Components

#### [MODIFY] [correlation.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/charts/correlation.py)
Update the `colorscale` definition in `build_corr_figure`:
- Correlation values map to `[-1, 1]`.
- Map colors dynamically so that `≤ 0.2` is colored green, `0.5` is yellow/orange, and `1.0` is red.
- Color stops in Plotly (scaled 0 to 1):
  - `0.0` (Correlation -1.0) -> `theme_tokens["GREEN"]`
  - `0.6` (Correlation 0.2) -> `theme_tokens["GREEN"]`
  - `0.75` (Correlation 0.5) -> `theme_tokens["WARNING"]`
  - `1.0` (Correlation 1.0) -> `theme_tokens["RED"]`

## Data Strategy
No changes to the underlying data models or storage. The callbacks will continue to fetch histories via `fetch_portfolio_history()` and `fetch_portfolio_series()` using the correct, dynamically selected period.

## Resolved Pain Points
- **Reactivity Gaps**: Fixes the issue where the correlation matrix and volatility charts remain stuck on the default `"1mo"` period.
- **Aesthetic/Intuitive Misalignment**: Prevents low positive correlations (like `0.22` or `0.38`) from displaying as warning colors (yellow/orange), making the matrix easy to read for portfolio diversification.

## Fallback States
If data is missing or holds fewer than 2 items for the selected period, standard empty states (`create_empty_fig`) are rendered. No changes to fallback logic.

## External Dependencies
None.

## External URLs
None.
