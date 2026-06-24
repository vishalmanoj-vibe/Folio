# Implementation Plan — Seamless Root-Level Installation & Launcher UX

This plan details the addition of root-level installation wrappers, automated desktop shortcut generation, and automatic browser launching for both macOS and Windows.

---

## Proposed Changes

### Root-Level Entry Points
We will add root-level entry scripts so users can just double-click them inside the project folder rather than running terminal commands.

#### [NEW] [setup.command](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/setup.command)
- A shell script checked in with executable permissions (`+x`).
- Automatically resolves its location, changes directory to the repository root, and runs `bash scripts/install.sh`.

#### [NEW] [setup.bat](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/setup.bat)
- A Windows batch file.
- Automatically resolves its location, changes directory to the repository root, and runs `scripts\install.bat`.

---

### Scripts Component

#### [MODIFY] [scripts/install.sh](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scripts/install.sh)
- **Desktop Shortcut Automation:** Automatically copy the generated `Folio.command` to `$HOME/Desktop/Folio.command` and ensure it has executable permissions (`chmod +x`).
- **Post-Install Launch Prompt:** At the end of the installation, prompt the user: *"Would you like to start Folio right now? (y/n)"*. If yes, run the launcher inline.
- **Improved Output styling:** Enhance logging readability with clean separation and emojis.

#### [MODIFY] [scripts/install.bat](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/scripts/install.bat)
- **Desktop Shortcut Automation:** Run a PowerShell inline script (via `-ExecutionPolicy Bypass`) to resolve the user's Desktop folder and create a standard Windows shortcut (`Folio.lnk`) pointing to the generated `folio_launch.bat`.
- **Browser Auto-Launch:** Update the generated `folio_launch.bat` template to include:
  1. A loop checking if port 8050 is active (up to 30 attempts).
  2. A command `start http://127.0.0.1:8050` to open the dashboard automatically in the user's default browser once ready.
- **Post-Install Launch Prompt:** Prompt the user: *"Would you like to start Folio right now? (Y/N)"*. If yes, execute `folio_launch.bat`.
- **Improved Output styling:** Add clear step formatting.

---

### Documentation

#### [MODIFY] [README.md](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/README.md)
- Update macOS installation instructions:
  - Just clone the repo and double-click `setup.command` in Finder (or run `bash setup.command` in terminal).
  - Clarify that a double-clickable launcher `Folio.command` is automatically placed on the Desktop.
- Update Windows installation instructions:
  - Just clone the repo and double-click `setup.bat` (or run it from Command Prompt).
  - Clarify that a shortcut `Folio` is automatically created on the Desktop.

---

## Verification Plan

### Manual Verification
1. **macOS Setup Execution:**
   - Run `bash setup.command` in terminal (or simulate double-clicking) to verify it executes `scripts/install.sh`.
   - Verify `Folio.command` is successfully generated and copied to the Desktop folder (`~/Desktop`).
   - Verify the launch prompt starts the application and launches Safari.
   - Run the Desktop `Folio.command` and verify it clears ports and launches normally.
2. **Windows Script Dry-Run / Code Review:**
   - Carefully review the generated batch script and PowerShell lines for path quoting and variable resolution to ensure bug-free execution on Windows.
