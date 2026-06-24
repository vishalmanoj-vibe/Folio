# Spec: Holdings and Transaction Table Deep-linking to Positions

## Feature Summary
Clicking on a ticker link in the holdings table (Overview page) or the recent transaction table will navigate the user to the Positions page and select that specific ticker's card/details directly, rather than falling back to the default first ticker (e.g., AINF).

## Modified/New Files List
- `callbacks/portfolio_callbacks.py` [MODIFY]
- `components/ui_helpers.py` [MODIFY]
- `callbacks/positions_callbacks.py` [MODIFY]

## Component IDs
No new Component IDs are introduced. The existing `url` and `positions-selected-ticker` are reused with updated inputs.

## Data Strategy
- Ticker links will change from `/positions` to `/positions?ticker=XYZ`.
- The `select_ticker` callback on the Positions page will read `url.search` on initial load (`current is None`) or when the URL is explicitly updated (`ctx.triggered_id == "url"`).
- We will validate that the target ticker exists in the user's current holdings before selecting it, falling back to the first available holding if not found or invalid.

## Resolved Pain Points
- **State Sync Bug Prevention**: If `url.search` is `?ticker=XYZ` and the user manually selects `ABC`, background refreshes of `portfolio-store` would ordinarily revert the selection back to `XYZ` if the search parameter is checked blindly. We prevent this by gating query parameter extraction with `ctx.triggered_id == "url"` or `current is None`.
- **Off-page Activation Prevention**: Pathname gating is enforced in `select_ticker` using `url.pathname` to prevent background callbacks from firing off-page.

## Fallback States
- If the ticker in the query parameter is invalid, not held, or empty, the page will default to selecting the first holding in the portfolio list.
- If no holdings exist, the page displays standard empty/skeleton states.

## External Dependencies
None.

## External URLs
None.
