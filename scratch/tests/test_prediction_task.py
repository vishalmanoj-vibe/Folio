import os
import sys

sys.path.append(os.getcwd())
import json
import logging
import random
import time
from datetime import datetime

import pandas as pd

from data.database import enqueue_task, get_connection

# Mocking enough to simulate Dash process environment
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_prediction")


def test_prediction_delegation():
    print("\n--- Folio Prediction Delegation Test ---")

    # 1. Check Prophet isolation
    if "prophet" in sys.modules:
        print("FAIL: Prophet already loaded in this process!")
        return
    else:
        print("PASS: Prophet is isolated (not in current process).")

    # 2. Prepare sample data
    dates = [
        (datetime.now() - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(100, 0, -1)
    ]
    values = [100 + i + random.random() * 5 for i in range(100)]

    print(f"Prepared {len(dates)} sample data points.")

    # 3. Enqueue task
    task_id = enqueue_task(
        "generate_prediction", {"dates": dates, "values": values, "horizon": "3mo"}, priority=7
    )
    print(f"Task enqueued: {task_id}")

    # 4. Poll for completion
    print("Waiting for worker to process task...", end="", flush=True)
    conn = get_connection()
    try:
        start_time = time.time()
        complete = False
        while time.time() - start_time < 60:  # 1 minute timeout
            row = conn.execute(
                "SELECT status, result FROM worker_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row and row["status"] == "complete":
                print("\nPASS: Task completed by worker.")
                complete = True
                break
            elif row and row["status"] == "failed":
                print(f"\nFAIL: Task failed. Result: {row['result']}")
                break
            print(".", end="", flush=True)
            time.sleep(2)

        if not complete:
            print("\nFAIL: Task timed out. Is the worker running?")
            return

        # 5. Check cache table
        # We need the cache key. Instead of re-generating it, we check for a fresh entry
        cache_row = conn.execute(
            "SELECT * FROM predictions_cache ORDER BY computed_at DESC LIMIT 1"
        ).fetchone()
        if cache_row:
            print(f"PASS: Found result in predictions_cache (Updated: {cache_row['computed_at']})")
        else:
            print("FAIL: No result found in predictions_cache table.")

    finally:
        conn.close()

    # 6. Final safety check
    if "prophet" in sys.modules:
        print("FAIL: Prophet was loaded into THIS process during the test!")
    else:
        print("PASS: Final isolation check successful. Memory remains lean.")


if __name__ == "__main__":
    try:
        test_prediction_delegation()
    except Exception as e:
        print(f"\nERROR: {e}")
