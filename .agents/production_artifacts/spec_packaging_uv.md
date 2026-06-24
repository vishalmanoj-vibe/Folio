# Spec — Phase 7: Distribution & Packaging
# Archived from .agents/production_artifacts/spec.md after build completion

## Feature Summary
Add a zero-friction installation path for Folio so anyone can install it from GitHub without Python experience. Uses `uv` (Astral's fast Python package manager) to handle all Python/venv setup automatically. On macOS, creates a native `.app` bundle. On Windows, creates a `.bat` shortcut.

## Approach: uv + Shell Installer
PyInstaller and PyWebView were explicitly ruled out due to past reliability issues with the complex dependency tree (Prophet, Playwright, pandas, yfinance, Dash together).

## New Files
| File | Purpose |
|------|---------|
| `install.sh` | macOS/Linux one-command installer — installs uv, Python 3.12, all deps, Playwright, prompts for API key, creates `Folio.app` |
| `install.bat` | Windows equivalent — uses PowerShell to install uv, same setup flow, creates `folio_launch.bat` shortcut |

## Modified Files
| File | Change |
|------|--------|
| `README.md` | Full Installation section rewrite: macOS, Windows, Linux, API key setup, Developer Setup |
| `docs/BUILD_HISTORY.md` | Phase 7 entry appended |

## Python Source Changes
**None.** Zero changes to app.py, launcher.py, settings.py, or any service file.
Data continues to live in `data/portfolio.db` within the project directory.

## Component IDs Added
None.

## External Dependencies Added
None — uv is downloaded by the installer script itself; it is not a Python package.
