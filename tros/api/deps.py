"""FastAPI dependencies — shared state injection (Phase 8)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from tros.api.execution_manager import ExecutionManager
from tros.llm.client import LLMClient


# Singleton execution manager (created once per process)
_manager: ExecutionManager | None = None


def get_execution_manager() -> ExecutionManager:
    """Get or create the singleton ExecutionManager."""
    global _manager
    if _manager is None:
        try:
            llm_client = LLMClient()
        except Exception:
            llm_client = None
        _manager = ExecutionManager(llm_client=llm_client)
    return _manager


def reset_execution_manager() -> None:
    """Reset the singleton (for testing)."""
    global _manager
    _manager = None
