"""Stress tests for SQLite persistence layer (Phase 10)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import pytest

from tros.api.db import init_db, get_connection
from tros.api.execution_manager import MissionExecution
from tros.api.repositories_sqlite import (
    SqliteEventRepository,
    SqliteExecutionRepository,
    SqliteMissionRepository,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "stress.db")
    init_db(path)
    return path


class TestConcurrentWrites:
    def test_concurrent_event_writes(self, db_path):
        """Multiple threads can write events concurrently."""
        repo = SqliteEventRepository(db_path=db_path)
        errors = []
        thread_count = 10
        events_per_thread = 20

        def writer(mission_id, count):
            try:
                for i in range(count):
                    repo.append(mission_id, {"type": f"event-{i}", "ts": time.time()})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(f"m-{t}", events_per_thread))
            for t in range(thread_count)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"
        # Verify all events were written
        for t in range(thread_count):
            events = repo.get_events(f"m-{t}")
            assert len(events) == events_per_thread

    def test_idempotency_key_uniqueness(self, db_path):
        """Idempotency keys remain unique under concurrent load."""
        repo = SqliteMissionRepository(db_path=db_path)
        errors = []

        def insert_key(idx):
            try:
                repo.save_idempotency_key(f"shared-key", f"mission-{idx}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=insert_key, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one mission should have the key
        result = repo.check_idempotency_key("shared-key")
        assert result is not None
        assert result.startswith("mission-")

    def test_read_during_write(self, db_path):
        """Reads succeed while writes are in progress."""
        repo = SqliteEventRepository(db_path=db_path)
        # Pre-populate some data
        for i in range(10):
            repo.append("m-read", {"type": f"pre-{i}"})

        results = []
        errors = []

        def reader():
            try:
                events = repo.get_events("m-read")
                results.append(len(events))
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(10):
                    repo.append("m-read", {"type": f"during-{i}"})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 2
        # Each reader should have found at least the pre-populated events
        assert all(r >= 10 for r in results)


class TestWALMode:
    def test_wal_mode_concurrent_readers(self, db_path):
        """WAL mode allows concurrent readers without blocking."""
        repo = SqliteExecutionRepository(db_path=db_path)
        # Write some data
        for i in range(5):
            repo.save(MissionExecution(
                mission_id=f"wal-{i}",
                execution_id=f"exec-{i}",
                status="COMPLETED",
            ))

        errors = []
        results = []

        def reader():
            try:
                all_execs = repo.get_all()
                results.append(len(all_execs))
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                repo.save(MissionExecution(
                    mission_id="wal-new",
                    execution_id="exec-new",
                    status="RUNNING",
                ))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 2
        assert all(r >= 5 for r in results)


class TestRecoveryAfterCrash:
    def test_data_survives_reopen(self, db_path):
        """Data persists after closing and reopening the database."""
        repo = SqliteEventRepository(db_path=db_path)
        repo.append("m1", {"type": "important-event"})
        repo.append("m1", {"type": "another-event"})

        # Simulate crash: open new connection
        repo2 = SqliteEventRepository(db_path=db_path)
        events = repo2.get_events("m1")
        assert len(events) == 2
        assert events[0]["type"] == "important-event"
