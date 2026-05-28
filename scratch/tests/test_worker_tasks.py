import json
import os
import sqlite3
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from data.database import enqueue_task, get_connection, init_db
from worker import TASK_HANDLERS, poll_tasks, prune_tasks, reset_stale_tasks


@pytest.fixture(autouse=True)
def setup_test_worker_db() -> Generator[None, None, None]:
    """Sets up an isolated, temporary SQLite database for worker task queue assertions."""
    test_db_path: str = "scratch/tests/test_worker.db"

    # Pre-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    with (
        patch("data.database.DB_PATH", test_db_path),
        patch("data.database._DB_INITIALIZED", False),
    ):
        init_db()  # Runs the full worker queue schemas
        yield

    # Post-clean
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def test_reset_stale_tasks() -> None:
    """Assert running/pending tasks older than 10 minutes are automatically timed out to failed."""
    test_db_path: str = "scratch/tests/test_worker.db"

    with patch("data.database.DB_PATH", test_db_path):
        # 1. Insert a mock task created 20 minutes ago
        stale_time: str = (datetime.now() - timedelta(minutes=20)).isoformat()

        conn: sqlite3.Connection = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO worker_tasks (task_id, task_type, payload, status, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                ("stale_task_123", "fetch_history", "{}", "running", 5, stale_time),
            )
            conn.commit()
        finally:
            conn.close()

        # 2. Run reset maintenance
        reset_stale_tasks()

        # 3. Assert status transitioned to failed
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM worker_tasks WHERE task_id = ?", ("stale_task_123",)
            ).fetchone()
            assert row is not None
            assert row["status"] == "failed"
            assert "timed out" in row["result"]
        finally:
            conn.close()


def test_prune_tasks() -> None:
    """Assert completed or failed tasks older than 24 hours are successfully purged from SQLite logs."""
    test_db_path: str = "scratch/tests/test_worker.db"

    with patch("data.database.DB_PATH", test_db_path):
        # 1. Insert a completed task done 48 hours ago, and a fresh one done 1 hour ago
        old_completed_time: str = (datetime.now() - timedelta(hours=48)).isoformat()
        fresh_completed_time: str = (datetime.now() - timedelta(hours=1)).isoformat()

        conn: sqlite3.Connection = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO worker_tasks (task_id, task_type, status, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("old_task", "fetch_history", "complete", old_completed_time, old_completed_time),
            )
            conn.execute(
                """
                INSERT INTO worker_tasks (task_id, task_type, status, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    "fresh_task",
                    "fetch_history",
                    "complete",
                    fresh_completed_time,
                    fresh_completed_time,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # 2. Run pruning maintenance
        prune_tasks()

        # 3. Assert old is deleted, fresh remains
        conn = get_connection()
        try:
            old_row = conn.execute(
                "SELECT * FROM worker_tasks WHERE task_id = ?", ("old_task",)
            ).fetchone()
            fresh_row = conn.execute(
                "SELECT * FROM worker_tasks WHERE task_id = ?", ("fresh_task",)
            ).fetchone()

            assert old_row is None
            assert fresh_row is not None
        finally:
            conn.close()


def test_poll_tasks_success() -> None:
    """Assert poller successfully pops pending tasks, triggers handlers, and updates statuses."""
    test_db_path: str = "scratch/tests/test_worker.db"

    # 1. Register a temporary mock handler in TASK_HANDLERS
    def dummy_handler(payload: dict[str, Any]) -> dict[str, str]:
        return {"result": f"Executed dummy for {payload.get('ticker')}"}

    TASK_HANDLERS["dummy_test_task"] = dummy_handler

    with patch("data.database.DB_PATH", test_db_path):
        # 2. Enqueue the task
        task_id: str = enqueue_task("dummy_test_task", payload={"ticker": "IOZ"}, priority=3)

        # 3. Trigger the Poller
        poll_tasks()

        # 4. Assert task status transitioned to complete and result is saved
        conn: sqlite3.Connection = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM worker_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            assert row is not None
            assert row["status"] == "complete"

            result_payload = json.loads(row["result"])
            assert result_payload["result"] == "Executed dummy for IOZ"
        finally:
            conn.close()

    # Clean up the global handler map
    TASK_HANDLERS.pop("dummy_test_task", None)
