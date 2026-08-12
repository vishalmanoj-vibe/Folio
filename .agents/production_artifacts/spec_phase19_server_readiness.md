# Feature Spec — Permanent Server Readiness & Browser Launch System

## Feature Summary
Fix the issue where double-clicking `folio.command` causes Safari to open prematurely with "Safari can't connect to server". Move browser launch ownership from the shell script to `launcher.py` so Safari is opened ONLY when the Dash HTTP server is verified to be 100% ready (responding with HTTP 200 OK), regardless of how long Python module imports take.

## Proposed Architectural Changes

### 1. `launcher.py` (Python Process Manager)
- Add a background thread `_wait_and_open_browser()` to `FolioLauncher`.
- Polls `http://127.0.0.1:8050/` using `urllib.request` or `requests` until `HTTP 200 OK` is returned (polling every 0.5s for up to 120s).
- Once HTTP 200 is confirmed, executes `open -a Safari http://127.0.0.1:8050/` (on macOS) or standard browser open (on other platforms).
- Ensures Safari opens EXACTLY once when the server is guaranteed live.

### 2. `scripts/Folio.command` (Shell Launcher)
- Simplify script: clear port 8050, launch `launcher.py`, and wait for `launcher.py` process to complete.
- Remove hardcoded 30s/45s polling loops and premature Safari launch calls from bash.

### 3. Desktop Shortcut Installer (`scripts/install_shortcut.py` / `.command`)
- Provide a clean script to generate/update `~/Desktop/folio.command`.

## Resolved Pain Points
- **Pain Point 1 (Premature Safari Launch)**: Eliminated. Safari will never be opened before Dash is accepting HTTP connections.
- **Pain Point 2 (Cold Start Delay Timeout)**: Eliminated. Whether Python module import takes 2s or 30s, browser launch waits until port 8050 is active.
- **Pain Point 3 (Desktop File Desync)**: Resolved by delegating logic to `launcher.py` so editing repo files instantly changes launcher behavior without needing to update Desktop shell scripts.
