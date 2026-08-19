"""Tests for Phase 9 repository abstraction."""

import pytest

from tros.api.execution_manager import MissionExecution
from tros.api.repositories import (
    EventRepository,
    ExecutionRepository,
    InMemoryEventRepository,
    InMemoryExecutionRepository,
    InMemoryMissionRepository,
    MissionRepository,
)


class TestInMemoryExecutionRepository:
    def test_save_and_get(self):
        repo = InMemoryExecutionRepository()
        execution = MissionExecution(mission_id="m1", execution_id="e1")
        repo.save(execution)
        result = repo.get_by_id("m1")
        assert result is not None
        assert result.mission_id == "m1"

    def test_get_nonexistent(self):
        repo = InMemoryExecutionRepository()
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self):
        repo = InMemoryExecutionRepository()
        repo.save(MissionExecution(mission_id="m1", execution_id="e1"))
        repo.save(MissionExecution(mission_id="m2", execution_id="e2"))
        all_execs = repo.get_all()
        assert len(all_execs) == 2

    def test_delete(self):
        repo = InMemoryExecutionRepository()
        repo.save(MissionExecution(mission_id="m1", execution_id="e1"))
        assert repo.delete("m1") is True
        assert repo.get_by_id("m1") is None

    def test_delete_nonexistent(self):
        repo = InMemoryExecutionRepository()
        assert repo.delete("nonexistent") is False


class TestInMemoryMissionRepository:
    def test_save_and_get_result(self):
        repo = InMemoryMissionRepository()
        repo.save_result("m1", {"status": "completed", "confidence": 0.9})
        result = repo.get_result("m1")
        assert result is not None
        assert result["confidence"] == 0.9

    def test_get_nonexistent(self):
        repo = InMemoryMissionRepository()
        assert repo.get_result("nonexistent") is None

    def test_list_missions(self):
        repo = InMemoryMissionRepository()
        repo.save_result("m1", {})
        repo.save_result("m2", {})
        missions = repo.list_missions()
        assert len(missions) == 2
        assert "m1" in missions
        assert "m2" in missions


class TestInMemoryEventRepository:
    def test_append_and_get_events(self):
        repo = InMemoryEventRepository()
        repo.append("m1", {"type": "mission.started"})
        repo.append("m1", {"type": "mission.completed"})
        events = repo.get_events("m1")
        assert len(events) == 2
        assert events[0]["type"] == "mission.started"

    def test_get_empty_events(self):
        repo = InMemoryEventRepository()
        assert repo.get_events("nonexistent") == []

    def test_clear(self):
        repo = InMemoryEventRepository()
        repo.append("m1", {"type": "event"})
        repo.clear("m1")
        assert repo.get_events("m1") == []


class TestProtocolConformance:
    def test_execution_repo_protocol(self):
        repo = InMemoryExecutionRepository()
        assert isinstance(repo, ExecutionRepository)

    def test_mission_repo_protocol(self):
        repo = InMemoryMissionRepository()
        assert isinstance(repo, MissionRepository)

    def test_event_repo_protocol(self):
        repo = InMemoryEventRepository()
        assert isinstance(repo, EventRepository)


class TestRepositoryIsolation:
    def test_repositories_are_independent(self):
        exec_repo = InMemoryExecutionRepository()
        mission_repo = InMemoryMissionRepository()
        event_repo = InMemoryEventRepository()

        exec_repo.save(MissionExecution(mission_id="m1", execution_id="e1"))
        mission_repo.save_result("m1", {"result": True})
        event_repo.append("m1", {"type": "event"})

        # Each repo should have its own data
        assert exec_repo.get_by_id("m1") is not None
        assert mission_repo.get_result("m1") is not None
        assert len(event_repo.get_events("m1")) == 1
