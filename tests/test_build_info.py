"""Tests for build version info (Phase 10)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tros.api.build_info import get_build_info
from tros.api.settings import reset_settings_cache


@pytest.fixture(autouse=True)
def _clean():
    reset_settings_cache()
    get_build_info.cache_clear()
    for key in list(os.environ):
        if key.startswith("TR_OS_"):
            os.environ.pop(key, None)
    yield
    reset_settings_cache()
    get_build_info.cache_clear()


class TestBuildInfo:
    def test_build_info_has_version(self):
        """Build info returns a version string."""
        info = get_build_info()
        assert "version" in info
        assert isinstance(info["version"], str)
        assert len(info["version"]) > 0

    def test_build_info_no_secrets(self):
        """Build info never contains sensitive data."""
        info = get_build_info()
        text = str(info)
        # No API keys, tokens, or env var values
        assert "sk-" not in text
        assert "DEEPSEEK_API_KEY" not in text
        assert "TR_OS_AUTH_SECRET" not in text
        # No internal file paths
        assert "/home/" not in text
        assert "C:\\" not in text

    def test_health_endpoint_includes_version(self):
        """Health endpoint includes build version."""
        from tros.api.app import create_app
        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "commit" in data
        assert "build_time" in data

    def test_metrics_endpoint_includes_version(self):
        """Metrics endpoint includes build version."""
        from tros.api.app import create_app
        client = TestClient(create_app())
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "commit" in data
        assert "build_time" in data
