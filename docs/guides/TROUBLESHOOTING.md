# Troubleshooting & Common Setup Issues

This document covers common installation, launch, and configuration issues you might encounter while using Folio.

---

### ⚠️ macOS: "install.command could not be executed because you do not have appropriate access privileges"
This happens if file permissions are lost (e.g., when downloading the repository as a ZIP file instead of using `git clone`).
- **Fix:** Open Terminal, navigate to the folder, and run:
  ```bash
  chmod +x scripts/install.command
  ```
  Then double-click or run the script again.

### ⚠️ macOS Gatekeeper: "unidentified developer" or "downloaded from the internet"
macOS security might block running the installer script or `Folio.app` on first launch.
- **Fix:** Right-click (`Ctrl + Click`) the file, select **Open**, and click **Open** in the warning dialog. Alternatively, go to **System Settings** → **Privacy & Security**, scroll down to the Security section, and click **Open Anyway**.

### ⚠️ Windows: PowerShell script execution is disabled / blocked
Windows may block downloading `uv` during installation due to PowerShell execution restrictions.
- **Fix:** Open PowerShell as Administrator and run:
  ```powershell
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Then run `scripts\install.bat` again. (Note: The installer automatically attempts to run with `-ExecutionPolicy Bypass` to mitigate this).

### ⚠️ Paths containing spaces
If the folder containing Folio resides in a path with spaces (e.g., `C:\Users\John Doe\OneDrive - Personal\folio`), it can occasionally cause path resolution bugs on Windows.
- **Fix:** Move the `folio` project folder to a path without spaces, such as `C:\Projects\folio` or `C:\folio`.

### ⚠️ OneDrive / Cloud Sync locks
If OneDrive, Dropbox, or iCloud is actively syncing the directory, the SQLite database (`portfolio.db`) or virtual environment files might get locked, causing installation or database errors.
- **Fix:** Pause synchronization during setup, or move the folder outside your sync directory (e.g., to your home directory `/Users/username/folio` or `C:\folio`).

### ⚠️ ETF Holdings scraping fails (Playwright issues)
If the holdings table for ETFs shows empty data and logs indicate Playwright is missing or failing:
- **Fix:** Manually trigger the Playwright installer inside the environment:
  - **macOS/Linux:** `uv run playwright install webkit`
  - **Windows:** `.venv\Scripts\playwright install webkit`

### ⚠️ Port 8050 is already in use
If you launch the app and get a port conflict or cannot connect:
- **Fix:** The launcher automatically tries to close processes occupying port 8050. If this fails:
  - **macOS/Linux:** Run `lsof -ti:8050 | xargs kill -9` in Terminal.
  - **Windows:** Open Command Prompt and run:
    ```cmd
    for /f "tokens=5" %a in ('netstat -ano ^| findstr :8050') do taskkill /PID %a /F
    ```
