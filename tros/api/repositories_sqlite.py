"""SQLite repository implementations (Phase 10).

Persistent repositories implementing the Phase 9 protocol interfaces:
- SqliteExecutionRepository: mission execution state
- SqliteMissionRepository: mission results and metadata
- SqliteEventRepository: SSE event log

Thread-safe via connection-per-operation pattern with WAL mode.
No secrets, prompts, or sensitive traces are stored.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from tros.api.db import get_connection
from tros.api.execution_manager import MissionExecution

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Execution Repository
# ---------------------------------------------------------------------------

class SqliteExecutionRepository:
    """SQLite-backed execution repository.

    Persists MissionExecution state. Thread-safe via connection-per-operation.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def save(self, execution: MissionExecution) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO executions
                   (id, mission_id, status, phase, progress,
                    submitted_at, started_at, completed_at, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    execution.execution_id,
                    execution.mission_id,
                    execution.status,
                    execution.phase,
                    execution.progress,
                    execution.started_at.isoformat(),
                    execution.started_at.isoformat(),
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    execution.error,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, mission_id: str) -> Optional[MissionExecution]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM executions WHERE mission_id = ?", (mission_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_execution(row)
        finally:
            conn.close()

    def get_all(self) -> list[MissionExecution]:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT * FROM executions").fetchall()
            return [self._row_to_execution(r) for r in rows]
        finally:
            conn.close()

    def delete(self, mission_id: str) -> bool:
        conn = self._conn()
        try:
            cursor = conn.execute(
                "DELETE FROM executions WHERE mission_id = ?", (mission_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def _row_to_execution(row: sqlite3.Row) -> MissionExecution:
        from tros.execution.cancellation import CancellationToken

        started_at = datetime.fromisoformat(row["submitted_at"])
        completed_at = (
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        )
        return MissionExecution(
            mission_id=row["mission_id"],
            execution_id=row["id"],
            status=row["status"],
            phase=row["phase"],
            progress=row["progress"],
            started_at=started_at,
            completed_at=completed_at,
            error=row["error"],
            cancellation_token=CancellationToken(),
        )


# ---------------------------------------------------------------------------
# Mission Repository
# ---------------------------------------------------------------------------

class SqliteMissionRepository:
    """SQLite-backed mission result repository."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def save_result(self, mission_id: str, result: Any) -> None:
        result_json = json.dumps(result, default=str) if result else None
        conn = self._conn()
        try:
            # Upsert: update result if mission row exists, insert otherwise
            existing = conn.execute(
                "SELECT mission_id FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE missions
                       SET result_json = ?, status = 'COMPLETED',
                           completed_at = ?
                       WHERE mission_id = ?""",
                    (result_json, _now_iso(), mission_id),
                )
            else:
                conn.execute(
                    """INSERT INTO missions
                       (mission_id, execution_id, origin, destination,
                        departure_date, status, result_json, created_at)
                       VALUES (?, ?, '', '', '', 'COMPLETED', ?, ?)""",
                    (mission_id, "", result_json, _now_iso()),
                )
            conn.commit()
        finally:
            conn.close()

    def get_result(self, mission_id: str) -> Optional[Any]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT result_json FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            if row is None or row["result_json"] is None:
                return None
            return json.loads(row["result_json"])
        finally:
            conn.close()

    def list_missions(self) -> list[str]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT mission_id FROM missions ORDER BY created_at DESC"
            ).fetchall()
            return [r["mission_id"] for r in rows]
        finally:
            conn.close()

    def create_mission(
        self,
        mission_id: str,
        execution_id: str,
        origin: str,
        destination: str,
        departure_date: str,
        idempotency_key: str | None = None,
    ) -> None:
        """Create a new mission record."""
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO missions
                   (mission_id, execution_id, origin, destination,
                    departure_date, status, created_at, idempotency_key)
                   VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?)""",
                (mission_id, execution_id, origin, destination,
                 departure_date, _now_iso(), idempotency_key),
            )
            conn.commit()
        finally:
            conn.close()

    def update_status(self, mission_id: str, status: str) -> None:
        """Update mission status."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE missions SET status = ? WHERE mission_id = ?",
                (status, mission_id),
            )
            conn.commit()
        finally:
            conn.close()

    def check_idempotency_key(self, key: str) -> Optional[str]:
        """Return mission_id if idempotency key exists, else None."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT mission_id FROM idempotency_keys WHERE key = ?",
                (key,),
            ).fetchone()
            return row["mission_id"] if row else None
        finally:
            conn.close()

    def save_idempotency_key(self, key: str, mission_id: str) -> None:
        """Store an idempotency key."""
        conn = self._conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO idempotency_keys
                   (key, mission_id, created_at) VALUES (?, ?, ?)""",
                (key, mission_id, _now_iso()),
            )
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Event Repository
# ---------------------------------------------------------------------------

class SqliteEventRepository:
    """SQLite-backed event log repository."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def append(self, mission_id: str, event: dict) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO events (mission_id, event_type, data_json, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (
                    mission_id,
                    event.get("type", "unknown"),
                    json.dumps(event, default=str),
                    event.get("timestamp", _now_iso()),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_events(self, mission_id: str, after_id: int = 0) -> list[dict]:
        """Return events for a mission, optionally after a given event ID.

        The after_id parameter supports Last-Event-ID replay.
        """
        conn = self._conn()
        try:
            if after_id > 0:
                rows = conn.execute(
                    """SELECT id, event_type, data_json, timestamp
                       FROM events
                       WHERE mission_id = ? AND id > ?
                       ORDER BY id ASC""",
                    (mission_id, after_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, event_type, data_json, timestamp
                       FROM events
                       WHERE mission_id = ?
                       ORDER BY id ASC""",
                    (mission_id,),
                ).fetchall()
            results = []
            for row in rows:
                event = json.loads(row["data_json"])
                event["_db_id"] = row["id"]
                results.append(event)
            return results
        finally:
            conn.close()

    def clear(self, mission_id: str) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "DELETE FROM events WHERE mission_id = ?", (mission_id,)
            )
            conn.commit()
        finally:
            conn.close()
