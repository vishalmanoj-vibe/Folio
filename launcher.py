# launcher.py
"""
Folio Process Launcher
======================
Manages both the Dash UI (app.py) and the Background Worker (worker.py).
Ensures process resilience and graceful shutdown.
"""

import sys
import time
import signal
import logging
import multiprocessing
from multiprocessing import Process

# Setup logging
from config.logging import setup_logging
setup_logging()
logger = logging.getLogger("launcher")

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
        
        # Register signals for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

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
            # 1. Start Dash if not running
            if not self.dash_process or not self.dash_process.is_alive():
                if self.dash_process:
                    logger.warning("Dash process died. Restarting...")
                self.dash_process = Process(target=run_dash, name="DashUI")
                self.dash_process.start()
                logger.info(f"Dash process started (PID: {self.dash_process.pid})")

            # 2. Start Worker if not running
            if not self.worker_process or not self.worker_process.is_alive():
                if self.worker_process:
                    logger.warning("Worker process died. Restarting in 5s...")
                    time.sleep(5) # Delay to prevent tight restart loops on crash
                self.worker_process = Process(target=run_background_worker, name="Worker")
                self.worker_process.start()
                logger.info(f"Worker process started (PID: {self.worker_process.pid})")

            # 3. Heartbeat
            time.sleep(5)
            
            # 4. Check if Dash was closed normally (e.g., app.run returned)
            if self.dash_process and not self.dash_process.is_alive():
                # If Dash exits with code 0, we assume intentional shutdown
                if self.dash_process.exitcode == 0:
                    logger.info("Dash process exited normally.")
                    self.handle_exit(None, None)
                else:
                    logger.error(f"Dash process exited with code {self.dash_process.exitcode}")

if __name__ == "__main__":
    # Ensure we use 'spawn' to avoid issues with database handles being inherited
    multiprocessing.set_start_method('spawn', force=True)
    
    launcher = FolioLauncher()
    launcher.launch()
