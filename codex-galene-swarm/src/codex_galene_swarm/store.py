from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TaskContract


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path + suffix
            if os.path.exists(candidate):
                os.chmod(candidate, 0o600)
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    require_jev INTEGER NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    contract_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, task_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                """
            )
            now = utc_now()
            db.execute(
                """UPDATE tasks SET status = 'failed', error = 'Interrupted by server restart', updated_at = ?
                   WHERE status IN ('queued', 'running') AND run_id IN
                   (SELECT run_id FROM runs WHERE status IN ('queued', 'running'))""",
                (now,),
            )
            db.execute(
                "UPDATE runs SET status = 'failed', updated_at = ? WHERE status IN ('queued', 'running')",
                (now,),
            )

    def create_run(self, run_id: str, goal: str, contracts: list[TaskContract], require_jev: bool) -> None:
        now = utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, 'queued', ?, 0, ?, ?)",
                (run_id, goal, int(require_jev), now, now),
            )
            db.executemany(
                "INSERT INTO tasks VALUES (?, ?, 'queued', ?, NULL, NULL, ?)",
                [(run_id, item.task_id, json.dumps(item.to_dict()), now) for item in contracts],
            )

    def set_run_status(self, run_id: str, status: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?", (status, utc_now(), run_id))

    def update_task(self, run_id: str, task_id: str, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE tasks SET status = ?, result_json = ?, error = ?, updated_at = ?
                   WHERE run_id = ? AND task_id = ? AND status IN ('queued', 'running')
                   AND EXISTS (SELECT 1 FROM runs WHERE run_id = ? AND cancel_requested = 0 AND status = 'running')""",
                (status, json.dumps(result) if result is not None else None, error, utc_now(), run_id, task_id, run_id),
            )
        return cursor.rowcount == 1

    def request_cancel(self, run_id: str) -> str | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = db.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                return None
            if run["status"] not in ("queued", "running"):
                return run["status"]
            now = utc_now()
            db.execute(
                "UPDATE runs SET cancel_requested = 1, status = 'cancelled', updated_at = ? WHERE run_id = ?",
                (now, run_id),
            )
            db.execute(
                "UPDATE tasks SET status = 'cancelled', updated_at = ? WHERE run_id = ? AND status IN ('queued', 'running')",
                (now, run_id),
            )
        return "cancelled"

    def is_cancel_requested(self, run_id: str) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT cancel_requested FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return bool(row and row["cancel_requested"])

    def get_run(self, run_id: str, include_results: bool = True) -> dict[str, Any] | None:
        with self._connect() as db:
            run = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not run:
                return None
            tasks = db.execute("SELECT * FROM tasks WHERE run_id = ? ORDER BY task_id", (run_id,)).fetchall()
        result = dict(run)
        result["require_jev"] = bool(result["require_jev"])
        result["cancel_requested"] = bool(result["cancel_requested"])
        result["tasks"] = []
        for row in tasks:
            item = dict(row)
            item["contract"] = json.loads(item.pop("contract_json"))
            raw_result = item.pop("result_json")
            item["result"] = json.loads(raw_result) if raw_result and include_results else None
            result["tasks"].append(item)
        return result

    def finish_if_terminal(self, run_id: str) -> None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            statuses = {row["status"] for row in db.execute(
                "SELECT status FROM tasks WHERE run_id = ?", (run_id,)
            )}
            terminal = {"passed", "rejected", "failed", "cancelled"}
            if statuses and statuses <= terminal:
                final = "failed" if statuses <= {"failed", "cancelled"} else "completed"
                db.execute(
                    """UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?
                       AND status = 'running' AND cancel_requested = 0""",
                    (final, utc_now(), run_id),
                )
