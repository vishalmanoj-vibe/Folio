@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM Folio — Installer  (Windows)
REM ─────────────────────────────────────────────────────────────────────────────
REM Usage: Double-click scripts\install.bat  OR  run from Command Prompt
REM
REM What it does:
REM   1. Installs uv (Python package manager) via PowerShell if not present
REM   2. Creates an isolated Python 3.12 virtual environment via uv
REM   3. Installs all Python dependencies from requirements.txt automatically
REM   4. Installs Playwright WebKit (ETF data scraper)
REM   5. Interactively configures .env (prompts for Gemini API key)
REM   6. Generates folio_launch.bat in the project root — pin to Start/Taskbar
REM ─────────────────────────────────────────────────────────────────────────────

SETLOCAL ENABLEDELAYEDEXPANSION

REM Resolve project root (parent of scripts\)
SET SCRIPTS_DIR=%~dp0
IF "%SCRIPTS_DIR:~-1%"=="\" SET SCRIPTS_DIR=%SCRIPTS_DIR:~0,-1%
FOR %%I IN ("%SCRIPTS_DIR%\..") DO SET FOLIO_DIR=%%~fI

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo        Folio  —  Installer  (Windows)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM ── Step 1: Check / install uv ────────────────────────────────────────────
echo [1/5] Checking for uv (Python package manager)...

WHERE uv >NUL 2>&1
IF ERRORLEVEL 1 (
    echo  uv not found — downloading via PowerShell...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    SET PATH=%USERPROFILE%\.local\bin;%APPDATA%\uv\bin;%PATH%
)

uv --version >NUL 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: uv install failed.
    echo  Install manually: https://docs.astral.sh/uv/getting-started/installation/
    pause & EXIT /B 1
)

FOR /F "tokens=*" %%V IN ('uv --version') DO SET UV_VER=%%V
echo  OK — %UV_VER%

REM ── Step 2: Python 3.12 venv ─────────────────────────────────────────────
echo.
echo [2/5] Setting up Python 3.12 environment...

CD /D "%FOLIO_DIR%"
uv python install 3.12 --quiet
IF EXIST "%FOLIO_DIR%\.venv" (
    echo  OK — Virtual environment already exists at .venv\ — reusing
) ELSE (
    uv venv .venv --python 3.12 --quiet
    echo  OK — virtual environment created at .venv\
)

REM ── Step 3: Install all Python dependencies ───────────────────────────────
echo.
echo [3/5] Installing all Python dependencies from requirements.txt...

uv pip install -r "%FOLIO_DIR%\requirements.txt" --quiet
echo  OK — all packages installed

REM ── Step 4: Playwright WebKit ─────────────────────────────────────────────
echo.
echo [4/5] Installing Playwright WebKit browser...

"%FOLIO_DIR%\.venv\Scripts\playwright" install webkit 2>NUL || (
    echo  WARNING: Playwright had warnings — usually fine.
    echo  If ETF scraping fails, run: uv run playwright install webkit
)
echo  OK — Playwright WebKit ready

REM ── Step 5: .env setup ───────────────────────────────────────────────────
echo.
echo [5/5] Configuring environment...

IF EXIST "%FOLIO_DIR%\.env" (
    echo  .env already exists — skipping. Delete it and re-run to reconfigure.
) ELSE (
    COPY "%FOLIO_DIR%\.env.example" "%FOLIO_DIR%\.env" >NUL

    echo.
    echo  Gemini API Key Setup
    echo  AI features require a free Gemini API key.
    echo  Get yours free at: https://aistudio.google.com
    echo.
    SET /P API_KEY="  Enter your Gemini API key (or press Enter to skip): "

    IF NOT "!API_KEY!"=="" (
        powershell -Command "(Get-Content '%FOLIO_DIR%\.env') -replace 'GEMINI_API_KEY=your_api_key_here', 'GEMINI_API_KEY=!API_KEY!' | Set-Content '%FOLIO_DIR%\.env'"
        echo  OK — API key saved to .env
    ) ELSE (
        echo  Skipped — add GEMINI_API_KEY to .env later to enable AI features
    )
)

REM ── Generate folio_launch.bat in scripts/ folder ───────────────────────────
echo.
echo [5/5] Generating folio_launch.bat launcher...

(
    echo @echo off
    echo REM Folio launcher — pin to Start Menu or Taskbar, or copy to Desktop
    echo CD /D "%FOLIO_DIR%"
    echo echo Clearing port 8050...
    echo for /f "tokens=5" %%%%a in ^('netstat -ano ^| findstr :8050'^) do ^(taskkill /PID %%%%a /F ^>NUL 2^>^&1^)
    echo echo Starting Folio...
    echo start /B "" "%FOLIO_DIR%\.venv\Scripts\python" "%FOLIO_DIR%\launcher.py"
    echo.
    echo echo Waiting for Folio server to start...
    echo set count=0
    echo :wait_loop
    echo curl -s http://127.0.0.1:8050 ^>nul 2^>^&1
    echo if %%errorlevel%% equ 0 ^(
    echo     goto launch_browser
    echo ^)
    echo set /a count+=1
    echo if %%count%% geq 30 ^(
    echo     echo Server start timed out. Please open http://127.0.0.1:8050 manually.
    echo     goto keep_alive
    echo ^)
    echo timeout /t 1 /nobreak ^>nul
    echo goto wait_loop
    echo.
    echo :launch_browser
    echo echo Folio is ready. Opening http://127.0.0.1:8050 in your default browser...
    echo start http://127.0.0.1:8050
    echo.
    echo :keep_alive
    echo timeout /t 2 /nobreak ^>nul
    echo netstat -ano ^| findstr :8050 ^>nul 2^>^&1
    echo if %%errorlevel%% equ 0 ^(
    echo     goto keep_alive
    echo ^)
    echo echo Folio server has stopped.
    echo pause
) > "%FOLIO_DIR%\scripts\folio_launch.bat"

echo  OK — folio_launch.bat created in scripts/ folder

REM ── Generate Folio.lnk Desktop shortcut ──────────────────────────────────
echo.
echo Generating Desktop shortcut...

powershell -ExecutionPolicy Bypass -Command "$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop); $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut(\"$desktop\Folio.lnk\"); $s.TargetPath = '%FOLIO_DIR%\scripts\folio_launch.bat'; $s.WorkingDirectory = '%FOLIO_DIR%'; $s.Description = 'Launch Folio Portfolio Dashboard'; $s.Save();"

if %errorlevel% equ 0 (
    echo  OK — Folio shortcut created on your Desktop
) else (
    echo  WARNING: Failed to create Desktop shortcut.
)

REM ── Done ──────────────────────────────────────────────────────────────────
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   Folio is installed and ready!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   Launch options:
echo     Double-click the "Folio" shortcut on your Desktop
echo     Double-click folio_launch.bat in scripts/ folder
echo     From Command Prompt:  uv run python launcher.py
echo.
echo   Then open http://127.0.0.1:8050 in your browser.
echo   Portfolio data is stored in: %FOLIO_DIR%\data\
echo.

SET /P START_NOW="Would you like to start Folio right now? (Y/N): "
IF /I "!START_NOW!"=="Y" (
    echo.
    echo Starting Folio...
    CALL "%FOLIO_DIR%\scripts\folio_launch.bat"
)
ENDLOCAL
