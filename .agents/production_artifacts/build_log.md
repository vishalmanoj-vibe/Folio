# Build Log — Permanent Server Readiness & Browser Launch Fix

## Summary of Changes Made
1. **[`launcher.py`](../../launcher.py)**:
   - Added `_wait_and_open_browser(self)` thread that actively polls `http://127.0.0.1:8050/` until `HTTP 200 OK` is returned.
   - Safari / default browser is opened at the exact millisecond port 8050 becomes responsive.
   - Prevents duplicate browser openings on process restart or headless mode.
2. **[`scripts/Folio.command`](../../scripts/Folio.command)**:
   - Removed fixed 30s/45s `sleep` loops and `osascript` browser calls from bash.
   - Streamlined script to delegate readiness verification and browser launching to `launcher.py`.
3. **[`scripts/install_shortcut.py`](../../scripts/install_shortcut.py)**:
   - Created installer script to simplify updating `~/Desktop/folio.command`.
