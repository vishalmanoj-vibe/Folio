# Technical Spec: Integrate Underlying Holdings into Allocation Treemap

## Goal
Replace the separate ETF Holdings bubble chart tab on the Analytics page (`/analytics`) with a new "Underlying Holdings" filter on the Allocation Treemap. This simplifies the page layout, provides a unified visual hierarchy, and reuses existing cached holdings data from SQLite.

## Stack & Technologies
- Dash / Plotly Python callbacks.
- SQLite cache (read-only for holdings metadata via `holdings_blended_data`).

## Key Component / Store IDs
- `treemap-mode`: SegmentedControl upgraded to include `"holdings"`.
- `portfolio-treemap`: Treemap graph on Analytics page.
- `holdings-freshness-note`: Div rendering data freshness or warnings about missing URL sources.
- `holdings-url-collapse`: Collapse panel containing the configure sources URL forms.

## Proposed Changes

### 1. Layout & Styling
* **[pages/analytics.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/analytics.py)**
  - Remove `dmc.TabsTab("ETF Holdings", value="holdings")` from `dmc.TabsList`.
  - Remove the `dmc.TabsPanel` corresponding to `"holdings"`.
  - Add option `{"label": "Underlying Holdings", "value": "holdings"}` to the SegmentedControl `treemap-mode`.
  - Relocate the `holdings-freshness-note` component directly below the `portfolio-treemap` component or adjacent to its description.

### 2. Treemap Component
* **[components/charts/treemap.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/charts/treemap.py)**
  - Add `holdings_data: dict[str, dict] | None = None` parameter to `build_portfolio_treemap()`.
  - Handle `mode == "holdings"`:
    - Compute underlying company absolute dollar value based on total portfolio value: `total_val * (weight / 100)`.
    - Limit underlying companies to the top 50 by blended weight.
    - Sum the remainder of weights into an "Other Underlying" block if it exceeds a threshold.
    - Style the treemap layout and blocks, displaying the blended weight percentage inside each block.
    - Show detailed tooltip descriptions on hover, listing the company name, absolute dollar value, total blended weight, and source ETF tickers.

### 3. Callbacks
* **[callbacks/chart_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/chart_callbacks.py)**
  - Remove `update_holdings_bubble_chart` callback.
  - Modify `portfolio_treemap` callback to output to `portfolio-treemap` (figure), `holdings-freshness-note` (children), and `holdings-url-collapse` (opened, with `allow_duplicate=True`).
  - Inside the callback, check if `mode == "holdings"`:
    - Fetch blended data using `holdings_blended_data(data)`.
    - If `blended_data` is empty, determine which tickers are missing cache data, build a warning note to populate `holdings-freshness-note`, return an empty figure, and toggle `holdings-url-collapse` to open.
    - Otherwise, build the treemap and set the freshness note to `"Holdings data loaded successfully."`.

### 4. Tests & Documentation
* **[scratch/tests/test_chart_components.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scratch/tests/test_chart_components.py)**
  - Remove `test_build_holdings_bubble_chart`.
  - Add `test_build_portfolio_treemap_holdings` testing the output elements, parents, and values of the underlying holdings treemap.
* **[docs/callback_ownership.md](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/docs/callback_ownership.md)**
  - Remove `holdings-bubble-chart` ownership.
  - Update `portfolio-treemap` outputs to list the multi-output signature.

---

## Resolved Pain Points
- **No Background Blocking**: The Dash thread only queries the cache via `holdings_blended_data()` without triggering a scraper block.
- **Empty States**: If holdings are missing, it provides instructions to add URLs and automatically opens the source management collapse.

## Fallback States
- **Empty/Error**: Renders `create_empty_fig("No underlying holdings data - add a source URL in ⚙ Configure Sources")` inside the treemap canvas.

## External Dependencies
- None.

## External URLs
- None.
