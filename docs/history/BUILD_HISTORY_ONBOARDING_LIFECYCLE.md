# Project Evolution & Build History — Onboarding & Lifecycle Era

> Back to [BUILD_HISTORY.md](BUILD_HISTORY.md)

This document details the desktop integration, installer automation, graceful shutdowns, and investor profile settings wizard phases of Folio, spanning version v2.4.0 to v2.7.0.

> [!NOTE]
> **Versioning & Phase Index Restart:**
> These phases follow the v2.0.0 memory hygiene architecture. They are numbered Phase 7 and Phase 8 in legacy logs due to a track numbering restart, but represent subsequent chronological development milestones (v2.4.0 and v2.5.0) after Phase 10.

---

## Phase 7: Distribution, Packaging & Setup UX (v2.4.0)
**Theme**: Making Folio installable by anyone directly from GitHub — no Python expertise required.

*   **uv-Based Installer**: Replaced the manual `pip install` setup process with a two-script installer (`install.sh` for macOS/Linux, `install.bat` for Windows). The installers use [uv](https://docs.astral.sh/uv/) to automatically download and configure Python 3.12, create an isolated `.venv`, install all dependencies, and install the Playwright WebKit browser — all in a single command.
*   **macOS App Bundle**: `install.sh` generates a native `Folio.app` bundle in the project root. The bundle contains an `Info.plist` and a shell launcher that resolves paths relative to its location, allowing it to be moved to `/Applications` or pinned to the Dock.
*   **Windows Launcher**: `install.bat` generates a `folio_launch.bat` shortcut in the `scripts/` folder after install, which can be pinned to the Start menu or Taskbar.
*   **Interactive API Key Setup**: The installer interactively prompts for a Gemini API key during setup and writes it to `.env` automatically, eliminating the manual copy-and-edit step for new users.
*   **Zero Source Code Changes**: No Python source files were modified. The app continues to use the project directory for all data (`data/portfolio.db`, `data/cache/`) and the existing `.env` for secrets, exactly as in development mode.
*   **README Overhaul**: Replaced the single "Setup" section with a comprehensive "Installation" section covering macOS (with `.app` instructions), Windows (with `.bat` instructions), Linux, API key configuration, and a separate Developer Setup path for contributors.
*   **scripts/ Subdirectory Installers**: Organized installers (`scripts/install.command` for macOS/Linux, `scripts/install.bat` for Windows) inside the `scripts/` folder, keeping the project root clean and clutter-free, while remaining fully double-clickable directly from Finder/Explorer.
*   **Automated Desktop Shortcuts**: Implemented automated desktop shortcut generation (`Folio.command` on macOS Desktop; `Folio.lnk` on Windows Desktop via PowerShell) so the user has immediate access to run the app with one click from their desktop.
*   **Resilient Virtual Environment Reuse**: Refactored the environment setup process to check for and reuse existing `.venv/` folders, preventing installation crashes on subsequent runs or app updates.
*   **Safe Permission Fallbacks**: Implemented graceful error catching during file copy operations (such as macOS `Desktop/` write permissions), warning the user to copy shortcuts manually rather than failing the installer.
*   **Browser Auto-Launch with Port Polling**: Configured the Windows launcher to check port 8050, wait for the Dash server to initialize, and automatically open the application in the user's default browser (matching the macOS experience).
*   **Detailed Setup Troubleshooting Guide**: Appended a comprehensive "Troubleshooting & Common Setup Issues" section to the README, detailing workarounds for macOS Gatekeeper blocks, Windows execution policy limits, directory path spacing, and Cloud sync locks.

---

## Phase 8: Browser-Close Graceful Shutdown (v2.5.0)
**Theme**: Lifecycle integration — the app process mirrors the browser window's lifetime.

*   **`beforeunload` Beacon**: Added `assets/browser_shutdown.js`, which registers a `window.beforeunload` listener and fires `navigator.sendBeacon('/shutdown?token=<TOKEN>')` when the user closes the tab or window. `sendBeacon` is used (not `fetch`) because it is guaranteed to dispatch even as the page tears down.
*   **3-Second Server Debounce**: A new Flask route `/shutdown` (registered on `app.server`) validates a shared one-time secret token and starts a `threading.Timer(3.0)` before sending `SIGTERM` to its own process. The delay prevents false positives on hard refreshes.
*   **SPA Navigation Cancel**: `browser_shutdown.js` intercepts `history.pushState`, `history.replaceState`, and `popstate` to fire `navigator.sendBeacon('/shutdown/cancel')` immediately on any Dash internal navigation. The Flask `/shutdown/cancel` route aborts the countdown if still running, so navigating between pages or refreshing the app **never** triggers a shutdown.
*   **Per-Run Secret Token**: `secrets.token_urlsafe(16)` generates a unique token at each app startup. It is embedded into the rendered HTML via a `<meta name="shutdown-token">` tag (injected through a new `get_index_string(token)` helper in `components/portfolio_layout.py`), so the JS can read it without any network round-trip.
*   **Launcher Compatibility**: When running via `launcher.py`, the SIGTERM from the Dash process causes the launcher's heartbeat loop to detect a non-zero exit code and call its existing `handle_exit()`, which gracefully terminates the background worker and exits the terminal. No changes to `launcher.py` were required.
*   **Files Changed**: `assets/browser_shutdown.js` (new), `app.py` (token generation + Flask routes), `components/portfolio_layout.py` (template function).

---

## Phase 11: Layman-Friendly Documentation & Onboarding Guidance (v2.6.0)
**Theme**: Standardizing documentation for ultimate clarity, lay-man accessibility, and detailed local developer/user guide mapping.

*   **Lay-Man Friendly Explanations**: Overhauled the root `README.md` to introduce the core concept of Folio using real-world analogies, making it clear for beginners.
*   **Finance-to-English Dictionary**: Added simple definitions of tickers, ETFs, P&L (intraday and total), transactions, ex-dividend dates, Sharpe Ratio, volatility, correlation, and forecasting.
*   **Local Double-Process Flowchart**: Built a clear ASCII mapping demonstrating the interactive relationship between the Browser UI, Dash Web App, Background Worker, and local relational SQLite database (`portfolio.db`).
*   **Bulletproof Setup & OS Troubleshooting**: Documented the installation process step-by-step for macOS and Windows, explaining what the installer scripts configure (uv, Python 3.12, WebKit Playwright, .env Gemini keys). Added direct solutions for permission privileges, macOS Gatekeeper blocks, Windows PowerShell policies, and cloud syncing database locks.
*   **Complete Workspace Reference**: Included a comprehensive folder map outlining the exact responsibility and location of all pages, callbacks, components, services, database queries, and testing suites.

---

## Phase 12: Investor Profile Settings in Onboarding Wizard (v2.7.0)
**Theme**: Improving onboarding setup flow to configure investor preferences directly during setup.

*   **Expanded Step 2 to Strategy & AI**: Renamed the wizard Step 2 from "AI Analyst" to "Strategy & AI" across `setup_portfolio.py`, `setup_ai.py`, and `setup_ready.py` to better reflect the new options.
*   **Strategy Settings Panel**: Added Investment Goal, Risk Tolerance, and Tax Bracket dropdowns to `setup_ai.py` (pre-populated with system defaults: Balanced, Moderate, 37%).
*   **Settings Persistence and Defaults**: Updated `handle_ai_setup` callback in `setup_callbacks.py` to save chosen strategy parameters to the SQLite database. If a user clicks "Skip for now", all parameters default gracefully to "Balanced", "Moderate", and "37%".
*   **Settings Loader**: Implemented a callback in `setup_callbacks.py` to load existing settings from SQLite when navigating to the page, ensuring proper state persistence.
*   **Footnote Instructions**: Added explanatory copy letting the user know they can update these settings anytime via the gear icon once the app is loaded.
*   **Files Changed**: `pages/setup_portfolio.py`, `pages/setup_ai.py`, `pages/setup_ready.py`, `callbacks/setup_callbacks.py`, `docs/reference/callback_ownership.md`, `.agents/skills/registry.md`.
