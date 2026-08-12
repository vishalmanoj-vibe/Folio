# Spec: Filter Holdings Sources to Held Tickers

Clean up the "Configure Sources" table under the Analytics page by displaying only the tickers actually held by the user or custom-configured by them, rather than unconditionally listing all default seed URLs. Also, prevent silent failures during Playwright installation by showing error output in installer scripts.

## Proposed Changes

### Modified Files

#### [MODIFY] [callbacks/chart_callbacks.py](../../callbacks/chart_callbacks.py)
- Update the `load_url_table` callback function.
- Change the `all_tickers` set construction from:
  `all_tickers = sorted(set(list(PROVIDER_SEED_URLS.keys()) + list(user_urls.keys()) + portfolio_tickers))`
  to:
  `all_tickers = sorted(set(list(user_urls.keys()) + portfolio_tickers))`
- Keep the default URL lookup and badge rendering logic unchanged.

#### [MODIFY] [scripts/install.command](../../scripts/install.command)
- Remove `--quiet 2>/dev/null` from the playwright installation command to expose any setup errors.

#### [MODIFY] [scripts/install.bat](../../scripts/install.bat)
- Remove `2>NUL` from the playwright installation command on Windows to expose any setup errors.

---

## Component IDs
No new component IDs will be introduced.

## Data Strategy
No changes to SQLite database schemas or `dcc.Store` contracts.

## Fallback States
If the user's portfolio is empty and they have no custom URLs configured, the callback renders a clean empty state message: `"No tickers configured."`.

## External Dependencies
No new dependencies are required. Playwright's browser binaries are being installed via command-line in the virtual environment to resolve the missing executable issue.
