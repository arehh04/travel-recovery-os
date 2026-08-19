"""Tests for SQLite repository implementations (Phase 10)."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone

import pytest

from tros.api.db import get_connection, init_db
from tros.api.execution_manager import MissionExecution
from tros.api.repositories import (
    EventRepository,
    ExecutionRepository,
    MissionRepository,
)
from tros.api.repositories_sqlite import (
    SqliteEventRepository,
    SqliteExecutionRepository,
    SqliteMissionRepository,
)
from tros.execution.cancellation import CancellationToken


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture(autouse=True)
def setup_db(db_path):
    """Initialize database before each test."""
    init_db(db_path)


# ---------------------------------------------------------------------------
# Execution Repository
# ---------------------------------------------------------------------------

class TestSqliteExecutionRepository:
    def test_save_and_get(self, db_path):
        repo = SqliteExecutionRepository(db_path=db_path)
        ex = MissionExecution(
            mission_id="m1",
            execution_id="e1",
            status="RUNNING",
            phase="FLIGHT_SEARCH",
            progress=0.5,
        )
        repo.save(ex)
        result = repo.get_by_id("m1")
        assert result is not None
        assert result.mission_id == "m1"
        assert result.execution_id == "e1"
        assert result.status == "RUNNING"
        assert result.phase == "FLIGHT_SEARCH"
        assert result.progress == 0.5

    def test_get_all(self, db_path):
        repo = SqliteExecutionRepository(db_path=db_path)
        for i in range(3):
            repo.save(MissionExecution(
                mission_id=f"m{i}", execution_id=f"e{i}", status="PENDING"
            ))
        all_execs = repo.get_all()
        assert len(all_execs) == 3

    def test_delete(self, db_path):
        repo = SqliteExecutionRepository(db_path=db_path)
        repo.save(MissionExecution(mission_id="m1", execution_id="e1"))
        assert repo.delete("m1") is True
        assert repo.get_by_id("m1") is None
        assert repo.delete("m1") is False

    def test_get_nonexistent(self, db_path):
        repo = SqliteExecutionRepository(db_path=db_path)
        assert repo.get_by_id("nonexistent") is None

    def test_update_existing(self, db_path):
        repo = SqliteExecutionRepository(db_path=db_path)
        ex = MissionExecution(mission_id="m1", execution_id="e1", status="PENDING")
        repo.save(ex)
        ex.status = "COMPLETED"
        ex.progress = 1.0
        ex.completed_at = datetime.now(timezone.utc)
        repo.save(ex)
        result = repo.get_by_id("m1")
        assert result.status == "COMPLETED"
        assert result.progress == 1.0

    def test_protocol_conformance(self):
        repo = SqliteExecutionRepository(db_path=":memory:")
        assert isinstance(repo, ExecutionRepository)


# ---------------------------------------------------------------------------
# Mission Repository
# ---------------------------------------------------------------------------

class TestSqliteMissionRepository:
    def test_save_and_get_result(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        result_data = {"recommendation": {"flight": "AK701"}, "confidence": 0.85}
        repo.save_result("m1", result_data)
        result = repo.get_result("m1")
        assert result is not None
        assert result["recommendation"]["flight"] == "AK701"
        assert result["confidence"] == 0.85

    def test_list_missions(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        repo.save_result("m1", {"data": 1})
        repo.save_result("m2", {"data": 2})
        missions = repo.list_missions()
        assert set(missions) == {"m1", "m2"}

    def test_get_nonexistent_result(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        assert repo.get_result("nonexistent") is None

    def test_create_mission(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        repo.create_mission(
            mission_id="m1",
            execution_id="e1",
            origin="KUL",
            destination="SIN",
            departure_date="2026-08-20",
            idempotency_key="key-123",
        )
        missions = repo.list_missions()
        assert "m1" in missions

    def test_idempotency_key(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        repo.save_idempotency_key("key-abc", "m1")
        assert repo.check_idempotency_key("key-abc") == "m1"
        assert repo.check_idempotency_key("key-xyz") is None

    def test_idempotency_key_duplicate_ignored(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        repo.save_idempotency_key("key-abc", "m1")
        repo.save_idempotency_key("key-abc", "m2")  # Should be ignored
        assert repo.check_idempotency_key("key-abc") == "m1"

    def test_update_status(self, db_path):
        repo = SqliteMissionRepository(db_path=db_path)
        repo.create_mission("m1", "e1", "KUL", "SIN", "2026-08-20")
        repo.update_status("m1", "RUNNING")
        conn = get_connection(db_path)
        row = conn.execute("SELECT status FROM missions WHERE mission_id = 'm1'").fetchone()
        conn.close()
        assert row["status"] == "RUNNING"

    def test_protocol_conformance(self):
        repo = SqliteMissionRepository(db_path=":memory:")
        assert isinstance(repo, MissionRepository)


# ---------------------------------------------------------------------------
# Event Repository
# ---------------------------------------------------------------------------

class TestSqliteEventRepository:
    def test_append_and_get(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        repo.append("m1", {"type": "mission.queued", "timestamp": "2026-01-01T00:00:00"})
        repo.append("m1", {"type": "mission.running", "timestamp": "2026-01-01T00:00:01"})
        events = repo.get_events("m1")
        assert len(events) == 2
        assert events[0]["type"] == "mission.queued"
        assert events[1]["type"] == "mission.running"

    def test_get_events_after_id(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        repo.append("m1", {"type": "e1"})
        repo.append("m1", {"type": "e2"})
        repo.append("m1", {"type": "e3"})
        # Get events after the first one
        events = repo.get_events("m1", after_id=1)
        assert len(events) == 2
        assert events[0]["type"] == "e2"

    def test_clear(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        repo.append("m1", {"type": "e1"})
        repo.append("m1", {"type": "e2"})
        repo.clear("m1")
        events = repo.get_events("m1")
        assert len(events) == 0

    def test_isolated_missions(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        repo.append("m1", {"type": "a"})
        repo.append("m2", {"type": "b"})
        assert len(repo.get_events("m1")) == 1
        assert len(repo.get_events("m2")) == 1

    def test_empty_mission(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        events = repo.get_events("nonexistent")
        assert events == []

    def test_protocol_conformance(self):
        repo = SqliteEventRepository(db_path=":memory:")
        assert isinstance(repo, EventRepository)


# ---------------------------------------------------------------------------
# Concurrent Access
# ---------------------------------------------------------------------------

class TestSqliteConcurrency:
    def test_concurrent_writes(self, db_path):
        repo = SqliteEventRepository(db_path=db_path)
        errors = []

        def writer(mission_id, count):
            try:
                for i in range(count):
                    repo.append(mission_id, {"type": f"event-{i}"})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(f"m{t}", 10))
            for t in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for t in range(5):
            events = repo.get_events(f"m{t}")
            assert len(events) == 10

    def test_db_file_created(self, tmp_path):
        db = str(tmp_path / "subdir" / "test.db")
        init_db(db)
        assert os.path.exists(db)
