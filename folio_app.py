# folio_app.py
"""
folio_app.py
============
Supervisor process for the packaged Folio desktop application.
Handles SQLite schema initialization, launches decoupled Dash UI
and background worker subprocesses, and manages a native pywebview window.
"""

import sys
import os
import subprocess
import socket
import time
import signal
import logging

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Setup basic logging for the supervisor
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] folio_supervisor: %(message)s"
)
logger = logging.getLogger("folio_supervisor")

def is_port_open(port=8050):
    """Check if a TCP port is open on localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def main():
    # 1. Initialize SQLite Database Schema before spawning subprocesses
    try:
        from data.database import init_db
        logger.info("Initializing SQLite database schemas...")
        init_db()
        logger.info("Database schemas successfully initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize SQLite database: {e}")
        sys.exit(1)

    # 2. Branch depending on command-line arguments (for reuse inside frozen executables)
    if "--dash" in sys.argv:
        logger.info("Starting Dash UI subprocess...")
        # Force headless mode to prevent browser spawning in child processes
        os.environ["FOLIO_HEADLESS"] = "1"
        try:
            from app import app
            app.run(debug=False, port=8050)
        except Exception as e:
            logger.critical(f"Dash process crashed: {e}")
            sys.exit(1)
        sys.exit(0)

    elif "--worker" in sys.argv:
        logger.info("Starting background worker subprocess...")
        try:
            from worker import run_worker
            run_worker()
        except KeyboardInterrupt:
            logger.info("Worker stopped by user signal.")
        except Exception as e:
            logger.critical(f"Worker process crashed: {e}")
            sys.exit(1)
        sys.exit(0)

    # 3. Default Supervisor flow
    logger.info("Starting supervisor orchestration...")
    
    # Decouple children processes from native browser opening by passing FOLIO_HEADLESS=1
    child_env = os.environ.copy()
    child_env["FOLIO_HEADLESS"] = "1"

    # Spawn processes using sys.executable (PyInstaller re-enters this exact file)
    logger.info("Spawning Dash UI process...")
    dash_proc = subprocess.Popen([sys.executable, "--dash"], env=child_env)
    
    logger.info("Spawning background worker process...")
    worker_proc = subprocess.Popen([sys.executable, "--worker"], env=child_env)

    # 4. Wait for Dash server port to be open
    logger.info("Waiting for Dash server to listen on port 8050...")
    start_time = time.time()
    opened = False
    while time.time() - start_time < 30: # 30s timeout
        if is_port_open(8050):
            opened = True
            break
        if dash_proc.poll() is not None:
            logger.error("Dash subprocess terminated prematurely.")
            break
        time.sleep(0.2)

    if not opened:
        logger.critical("Dash server port 8050 failed to open in 30 seconds.")
        dash_proc.terminate()
        worker_proc.terminate()
        sys.exit(1)

    logger.info("Dash server is live on 127.0.0.1:8050.")

    # 5. Resolve first-run vs active user route
    try:
        from data.repository import PortfolioRepository
        repo = PortfolioRepository()
        has_txns = len(repo.load_transactions()) > 0
    except Exception as e:
        logger.error(f"Error checking transaction logs: {e}")
        has_txns = False

    initial_url = "http://127.0.0.1:8050/" if has_txns else "http://127.0.0.1:8050/setup/portfolio"
    logger.info(f"Opening pywebview window with route: {initial_url}")

    # 6. Start pywebview window
    try:
        import webview
        window = webview.create_window(
            title="Folio",
            url=initial_url,
            width=1280,
            height=800,
            min_size=(900, 600)
        )
        
        def on_closed():
            logger.info("Main window closed. Cleaning up child processes...")
            try:
                dash_proc.terminate()
            except Exception:
                pass
            try:
                worker_proc.terminate()
            except Exception:
                pass
            
            # Allow graceful termination, then enforce kill
            time.sleep(0.5)
            try:
                dash_proc.kill()
            except Exception:
                pass
            try:
                worker_proc.kill()
            except Exception:
                pass
            logger.info("Cleanup completed. Exiting supervisor.")

        window.events.closed += on_closed
        webview.start()

    except Exception as e:
        logger.error(f"pywebview GUI failed to launch: {e}")
        logger.info("Fallback: supervisor running in console mode. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Supervisor terminated by user.")
        finally:
            logger.info("Cleaning up subprocesses...")
            dash_proc.terminate()
            worker_proc.terminate()
            time.sleep(0.5)
            dash_proc.kill()
            worker_proc.kill()

if __name__ == "__main__":
    main()
