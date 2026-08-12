# Onboarding Graceful Restart Spec

Gracefully restart the Dash application process when the onboarding wizard is completed. This forces the restarted server to read the newly-saved transactions and portfolio data from SQLite at startup, ensuring all pages load correctly without requiring manual command-line process restarts.

## Proposed Changes

### Modified Files

#### [MODIFY] [launcher.py](../../launcher.py)
- Detect if the Dash process exited with code `3` (restart request).
- Log a clean restart request instead of a crash warning.
- Automatically start a new Dash process immediately.

#### [MODIFY] [callbacks/setup_callbacks.py](../../callbacks/setup_callbacks.py)
- Add a helper `request_restart()` that starts a background `threading.Timer(1.0)` to run `os._exit(3)`.
- Call `request_restart()` when `setup-ready-launch-btn` is clicked (onboarding finished).

---

## Component IDs
No new component IDs will be introduced.

## Data Strategy
No changes to SQLite database schemas or `dcc.Store` contracts.

## Fallback States
No changes to fallback states.

## External Dependencies
No external dependencies.
