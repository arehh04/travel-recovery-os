"""FastAPI dependencies — shared state injection (Phase 8/9/10)."""

from __future__ import annotations

from typing import Any

from tros.api.execution_manager import ExecutionManager
from tros.api.settings import Environment, get_settings
from tros.llm.client import LLMClient

# Singleton execution manager (created once per process)
_manager: ExecutionManager | None = None


def get_execution_manager() -> ExecutionManager:
    """Get or create the singleton ExecutionManager.

    In production/testing, uses SQLite-backed repositories.
    In development, uses in-memory repositories (backward compatible).
    """
    global _manager
    if _manager is None:
        settings = get_settings()
        try:
            llm_client = LLMClient()
        except Exception:
            llm_client = None

        kwargs: dict[str, Any] = dict(
            llm_client=llm_client,
            max_workers=settings.max_workers,
            max_concurrent_missions=settings.max_concurrent_missions,
            mission_timeout_sec=settings.mission_timeout_sec,
            idempotency_ttl_sec=settings.idempotency_ttl_sec,
        )

        # In production/testing, use SQLite persistence
        if settings.environment in (Environment.PRODUCTION, Environment.TESTING):
            try:
                from tros.api.db import init_db
                from tros.api.repositories_sqlite import (
                    SqliteEventRepository,
                    SqliteExecutionRepository,
                    SqliteMissionRepository,
                )
                init_db()
                kwargs["execution_repo"] = SqliteExecutionRepository()
                kwargs["mission_repo"] = SqliteMissionRepository()
                kwargs["event_repo"] = SqliteEventRepository()
            except Exception:
                pass  # Fall back to in-memory if DB unavailable

        _manager = ExecutionManager(**kwargs)
    return _manager


def reset_execution_manager() -> None:
    """Reset the singleton (for testing)."""
    global _manager
    _manager = None
