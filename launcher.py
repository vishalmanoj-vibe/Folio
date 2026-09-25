# launcher.py
"""
Folio Process Launcher
======================
Manages both the Dash UI (app.py) and the Background Worker (worker.py).
Ensures process resilience and graceful shutdown.
"""

import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import threading
import time
from multiprocessing import Process

# Setup logging
from config.logging import setup_logging

setup_logging()
logger = logging.getLogger("launcher")


def get_process_memory_mb(pid):
    """Get process memory usage in MB using 'ps'."""
    try:
        output = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)])
        return int(output.strip()) / 1024
    except:
        return 0


def ensure_files_local():
    """Download OneDrive/iCloud 'online-only' placeholders before Dash imports them (BUG-027).

    macOS File Provider evicts unused files to the cloud. Reading an evicted file blocks
    ~1s while it downloads, so importing pandas/plotly/dash from evicted files makes
    startup look frozen for an hour. Hydrating them in parallel up front takes seconds.
    """
    if sys.platform != "darwin":
        return
    from concurrent.futures import ThreadPoolExecutor

    SF_DATALESS = 0x40000000  # st_flags bit: content lives only in the cloud
    skip_dirs = {".git", ".venv", "htmlcov", "scratch", "screenshots", "logs"}
    project_dir = os.path.dirname(os.path.abspath(__file__))
    roots = [project_dir]
    if "/Library/CloudStorage/" in sys.prefix or "/Mobile Documents/" in sys.prefix:
        logger.warning(
            f"Python environment is inside a cloud-synced folder ({sys.prefix}). "
            "Re-run scripts/install.command to move it to ~/.folio/venv."
        )
        roots.append(sys.prefix)

    pending = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if root == project_dir:
                dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    if os.lstat(path).st_flags & SF_DATALESS:
                        pending.append(path)
                except OSError:
                    pass
    if not pending:
        return

    logger.warning(
        f"{len(pending)} file(s) are online-only in OneDrive/iCloud — downloading before "
        "startup. In Finder, right-click the project folder → 'Always Keep on This Device'."
    )

    def _hydrate(path):
        try:
            with open(path, "rb") as f:
                while f.read(1 << 20):
                    pass
        except OSError:
            pass

    with ThreadPoolExecutor(max_workers=32) as pool:
        for i, _ in enumerate(pool.map(_hydrate, pending), 1):
            if i % 500 == 0 or i == len(pending):
                logger.info(f"Downloaded {i}/{len(pending)} online-only file(s)")


def run_dash():
    """Wrapper to run the Dash app."""
    # We import app inside the function to ensure the worker process
    # doesn't accidentally initialize Dash.
    try:
        from app import app

        # Dash's run method is blocking
        app.run(debug=False, port=8050, host="0.0.0.0")
    except Exception as e:
        logger.error(f"Dash process error: {e}")
        sys.exit(1)


def run_background_worker():
    """Wrapper to run the background worker."""
    try:
        from worker import run_worker

        run_worker()
    except Exception as e:
        logger.error(f"Worker process error: {e}")
        sys.exit(1)


class FolioLauncher:
    def __init__(self):
        self.dash_process = None
        self.worker_process = None
        self.running = True
        self.last_mem_check = 0
        self.browser_opened = False

        # Register signals for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def _wait_and_open_browser(self):
        """Polls port 8050 until Dash server is listening and returns HTTP 200 OK."""
        import socket
        import urllib.request
        import webbrowser

        url = "http://127.0.0.1:8050/"
        start_time = time.time()
        logger.info("Waiting for Dash server to respond on port 8050...")

        # Phase 1: Wait for port 8050 to accept TCP connection
        port_open = False
        while self.running and (time.time() - start_time < 120):
            try:
                with socket.create_connection(("127.0.0.1", 8050), timeout=0.5):
                    port_open = True
                    break
            except Exception:
                time.sleep(0.5)

        if not port_open:
            logger.warning("Dash server port 8050 did not open after 120s.")
            return

        # Phase 2: Verify HTTP 200 OK
        while self.running and (time.time() - start_time < 120):
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    if resp.status == 200:
                        logger.info("Dash server verified live on port 8050! Opening browser.")
                        if sys.platform == "darwin":
                            # `open <url>` uses the system default browser
                            subprocess.run(["open", url], check=False)
                        else:
                            webbrowser.open_new(url)
                        return
            except Exception:
                time.sleep(0.5)

        logger.warning("Dash server readiness check timed out after 120s.")

    def handle_exit(self, sig, frame):
        """Signal handler for graceful shutdown."""
        logger.info("\n  Shutting down Folio... stopping all processes.")
        self.running = False
        self.stop_all()
        sys.exit(0)

    def stop_all(self):
        """Terminate both processes."""
        if self.worker_process and self.worker_process.is_alive():
            logger.info("Stopping background worker...")
            self.worker_process.terminate()
            self.worker_process.join(timeout=5)

        if self.dash_process and self.dash_process.is_alive():
            logger.info("Stopping Dash UI...")
            self.dash_process.terminate()
            self.dash_process.join(timeout=5)

    def launch(self):
        """Main launcher loop."""
        logger.info("Launching Folio — Process Manager active.")

        while self.running:
            # 0. Check if Dash exited intentionally BEFORE deciding to restart.
            #    Exit code  0   = app.run() returned normally (rare).
            #    Exit code -15  = SIGTERM — browser-close shutdown beacon fired this.
            #    Any other code = genuine crash → fall through to restart logic below.
            if self.dash_process and not self.dash_process.is_alive():
                exit_code = self.dash_process.exitcode
                if exit_code == 3:
                    logger.info("Dash process requested a graceful restart (onboarding finished).")
                elif exit_code in (0, -signal.SIGTERM):
                    logger.info(
                        f"Dash process exited cleanly (code {exit_code}) — "
                        "browser window was closed. Shutting down Folio."
                    )
                    self.handle_exit(None, None)
                    return  # handle_exit calls sys.exit(0); this is a safety guard

            # 1. Start Dash if not running (only reached on crash or restart request)
            if not self.dash_process or not self.dash_process.is_alive():
                if self.dash_process:
                    os.environ["FOLIO_RESTARTED"] = "1"
                    if exit_code == 3:
                        logger.info("Starting new Dash UI process...")
                    else:
                        logger.warning("Dash process crashed. Restarting...")
                self.dash_process = Process(target=run_dash, name="DashUI")
                self.dash_process.start()
                logger.info(f"Dash process started (PID: {self.dash_process.pid})")

                # Trigger background browser check thread on initial launch
                if (
                    not self.browser_opened
                    and os.environ.get("FOLIO_RESTARTED") != "1"
                    and os.environ.get("FOLIO_HEADLESS") != "1"
                ):
                    self.browser_opened = True
                    threading.Thread(
                        target=self._wait_and_open_browser, daemon=True, name="BrowserLauncher"
                    ).start()

                # Give DashUI time to read SQLite snapshot before Worker starts heavy writes
                time.sleep(1.5)

            # 2. Start Worker if not running
            if not self.worker_process or not self.worker_process.is_alive():
                if self.worker_process:
                    logger.warning("Worker process died. Restarting in 5s...")
                    time.sleep(5)  # Delay to prevent tight restart loops on crash
                self.worker_process = Process(target=run_background_worker, name="Worker")
                self.worker_process.start()
                logger.info(f"Worker process started (PID: {self.worker_process.pid})")

            # 3. Heartbeat
            time.sleep(5)

            # 4. Monitor Worker Memory (Every 60s)
            if self.worker_process and self.worker_process.is_alive():
                current_time = time.time()
                if current_time - self.last_mem_check > 60:
                    self.last_mem_check = current_time
                    mem_mb = get_process_memory_mb(self.worker_process.pid)
                    if mem_mb > 800:
                        logger.warning(
                            f"Worker memory high ({mem_mb:.1f}MB). Restarting process..."
                        )
                        self.worker_process.terminate()
                        # The loop will restart it automatically next iteration


if __name__ == "__main__":
    # Ensure we use 'spawn' to avoid issues with database handles being inherited
    multiprocessing.set_start_method("spawn", force=True)

    ensure_files_local()
    launcher = FolioLauncher()
    launcher.launch()
