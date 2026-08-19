"""Build version metadata (Phase 10).

Provides build information for health/metrics endpoints:
- version: from pyproject.toml or TR_OS_BUILD_VERSION env var
- commit_sha: from git or TR_OS_COMMIT_SHA env var
- build_time: from TR_OS_BUILD_TIME env var
- environment: from settings

Never exposes: secrets, internal paths, raw environment variables.
"""

from __future__ import annotations

import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Safe fallback version
_FALLBACK_VERSION = "0.10.0"


def _read_pyproject_version() -> str:
    """Read version from pyproject.toml without importing toml."""
    try:
        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version"):
                    # Parse: version = "0.1.0"
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return _FALLBACK_VERSION


def _read_git_sha() -> str:
    """Read current git commit SHA. Returns 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]  # Short SHA
    except Exception:
        pass
    return "unknown"


@lru_cache(maxsize=1)
def get_build_info() -> dict:
    """Return build metadata. Cached per process lifetime.

    Safe fields only — never includes secrets or internal paths.
    """
    version = os.environ.get("TR_OS_BUILD_VERSION") or _read_pyproject_version()
    commit_sha = os.environ.get("TR_OS_COMMIT_SHA") or _read_git_sha()
    build_time = os.environ.get("TR_OS_BUILD_TIME", "")

    from tros.api.settings import get_settings
    settings = get_settings()

    return {
        "version": version,
        "commit": commit_sha,
        "build_time": build_time,
        "environment": settings.environment.value,
    }
