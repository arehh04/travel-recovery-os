"""Tests for Phase 9 execution manager hardening."""

import os
import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from tros.api.execution_manager import (
    ExecutionManager,
    MissionExecution,
    QueueFullError,
)
from tros.api.settings import reset_settings_cache
from tros.api.deps import reset_execution_manager


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    reset_execution_manager()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()
    reset_execution_manager()


class TestConfigurableWorkers:
    def test_default_workers(self):
        manager = ExecutionManager(llm_client=None, max_workers=4)
        assert manager._max_workers == 4

    def test_custom_workers(self):
        manager = ExecutionManager(llm_client=None, max_workers=8)
        assert manager._max_workers == 8


class TestQueueOverflow:
    def test_queue_full_raises(self):
        """When max concurrent missions is reached, submit should raise QueueFullError."""
        manager = ExecutionManager(
            llm_client=None,
            max_workers=2,
            max_concurrent_missions=1,
        )
        # Mock the service to block (simulating a slow mission)
        manager._service = MagicMock()
        event = threading.Event()
        manager._service.run.side_effect = lambda **kw: event.wait(timeout=5)

        # Submit first mission (should succeed)
        manager.submit({"origin": "KUL", "destination": "SIN", "departure_date": "2026-01-01"})

        # Second should raise QueueFullError
        with pytest.raises(QueueFullError):
            manager.submit({"origin": "KUL", "destination": "NRT", "departure_date": "2026-01-01"})

        # Clean up
        event.set()
        manager.shutdown(wait=False)


class TestTimeoutEnforcement:
    def test_mission_timeout_setting(self):
        manager = ExecutionManager(llm_client=None, mission_timeout_sec=30)
        assert manager._mission_timeout == 30


class TestCleanupOldMissions:
    def test_cleanup_completed(self):
        manager = ExecutionManager(llm_client=None, idempotency_ttl_sec=1)
        # Manually add a completed mission
        from datetime import datetime, timezone, timedelta
        execution = MissionExecution(
            mission_id="m1",
            execution_id="e1",
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        with manager._lock:
            manager._missions["m1"] = execution

        removed = manager.cleanup_completed(ttl_sec=1)
        assert removed == 1
        assert "m1" not in manager._missions

    def test_cleanup_preserves_active(self):
        manager = ExecutionManager(llm_client=None, idempotency_ttl_sec=1)
        from datetime import datetime, timezone, timedelta
        # Active mission
        active = MissionExecution(
            mission_id="m1",
            execution_id="e1",
            status="RUNNING",
        )
        # Old completed mission
        completed = MissionExecution(
            mission_id="m2",
            execution_id="e2",
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        with manager._lock:
            manager._missions["m1"] = active
            manager._missions["m2"] = completed

        removed = manager.cleanup_completed(ttl_sec=1)
        assert removed == 1
        assert "m1" in manager._missions
        assert "m2" not in manager._missions


class TestGracefulShutdown:
    def test_shutdown_method_exists(self):
        manager = ExecutionManager(llm_client=None)
        manager.shutdown(wait=False)
        # Should not raise


class TestExceptionIsolation:
    def test_exception_doesnt_crash_pool(self):
        """One failing mission shouldn't prevent others from running."""
        manager = ExecutionManager(llm_client=None, max_workers=2)
        mock_service = MagicMock()
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Simulated failure")
            return MagicMock(status="completed", confidence=0.9)

        mock_service.run.side_effect = side_effect
        manager._service = mock_service

        # First mission will fail
        m1 = manager.submit({"origin": "KUL", "destination": "SIN", "departure_date": "2026-01-01"})
        time.sleep(0.5)

        # Second mission should still work
        m2 = manager.submit({"origin": "KUL", "destination": "NRT", "departure_date": "2026-01-01"})
        time.sleep(0.5)

        assert m1.status == "FAILED"
        # m2 should have run (might be COMPLETED or still RUNNING depending on timing)
        assert m2.status in ("COMPLETED", "RUNNING")
        manager.shutdown(wait=False)


class TestMetrics:
    def test_metrics_tracking(self):
        manager = ExecutionManager(llm_client=None)
        metrics = manager.get_metrics()
        assert "total_submitted" in metrics
        assert "active_missions" in metrics
        assert metrics["total_submitted"] == 0

    def test_metrics_increment_on_submit(self):
        manager = ExecutionManager(llm_client=None)
        mock_service = MagicMock()
        mock_service.run.return_value = MagicMock(status="completed", confidence=0.9)
        manager._service = mock_service

        manager.submit({"origin": "KUL", "destination": "SIN", "departure_date": "2026-01-01"})
        time.sleep(0.3)

        metrics = manager.get_metrics()
        assert metrics["total_submitted"] >= 1
        manager.shutdown(wait=False)
