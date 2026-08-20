"""Tests for Docker hardening (Phase 10)."""

from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerignore:
    def test_dockerignore_exists(self):
        """.dockerignore exists."""
        path = os.path.join(_ROOT, ".dockerignore")
        assert os.path.exists(path), ".dockerignore not found"

    def test_dockerignore_excludes_critical_patterns(self):
        """.dockerignore excludes tests, .git, __pycache__, .env."""
        path = os.path.join(_ROOT, ".dockerignore")
        content = open(path, encoding="utf-8").read()
        required = [".git/", "__pycache__/", "tests/", ".env", "*.pyc"]
        for pattern in required:
            assert pattern in content, f".dockerignore missing: {pattern}"

    def test_dockerignore_excludes_data_dir(self):
        """.dockerignore excludes data/ (runtime mount only)."""
        path = os.path.join(_ROOT, ".dockerignore")
        content = open(path, encoding="utf-8").read()
        assert "data/" in content


class TestDockerfile:
    def test_dockerfile_pins_base_images(self):
        """Dockerfile uses pinned base image versions."""
        path = os.path.join(_ROOT, "Dockerfile")
        content = open(path, encoding="utf-8").read()
        # Should NOT use generic tags
        assert "FROM node:20-alpine" not in content, "Node base must be pinned"
        assert "FROM python:3.12-slim" not in content or "FROM python:3.12.8-slim" in content, (
            "Python base must be pinned"
        )

    def test_dockerfile_has_labels(self):
        """Dockerfile includes OCI labels."""
        path = os.path.join(_ROOT, "Dockerfile")
        content = open(path, encoding="utf-8").read()
        assert "LABEL" in content
        assert "org.opencontainers.image.version" in content

    def test_dockerfile_no_secrets(self):
        """Dockerfile does not hardcode secrets."""
        path = os.path.join(_ROOT, "Dockerfile")
        content = open(path, encoding="utf-8").read()
        assert "sk-" not in content
        assert "password" not in content.lower().split("#")[0]  # ignore comments

    def test_dockerfile_has_stop_signal(self):
        """Dockerfile has STOPSIGNAL for graceful shutdown."""
        path = os.path.join(_ROOT, "Dockerfile")
        content = open(path, encoding="utf-8").read()
        assert "STOPSIGNAL" in content

    def test_dockerfile_has_healthcheck(self):
        """Dockerfile has HEALTHCHECK directive."""
        path = os.path.join(_ROOT, "Dockerfile")
        content = open(path, encoding="utf-8").read()
        assert "HEALTHCHECK" in content


class TestDockerComposeProd:
    def test_resource_limits(self):
        """docker-compose.prod.yml has resource limits."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        assert "memory" in content or "mem_limit" in content, "Missing memory limits"
        assert "cpus" in content, "Missing CPU limits"

    def test_logging_config(self):
        """docker-compose.prod.yml has logging config."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        assert "logging:" in content
        assert "json-file" in content
        assert "max-size" in content

    def test_sqlite_volume_mounted(self):
        """docker-compose.prod.yml mounts SQLite data volume."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        assert "./data:/app/data" in content

    def test_no_hardcoded_secrets(self):
        """docker-compose.prod.yml uses env var references, not hardcoded secrets."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        assert "sk-" not in content
        # Secrets should be ${VAR} references
        assert "${DEEPSEEK_API_KEY}" in content
        assert "${TR_OS_AUTH_SECRET}" in content

    def test_build_version_env(self):
        """docker-compose.prod.yml passes build version env vars."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        assert "TR_OS_BUILD_VERSION" in content
        assert "TR_OS_COMMIT_SHA" in content

    def test_nginx_pinned_image(self):
        """docker-compose.prod.yml uses pinned nginx image."""
        path = os.path.join(_ROOT, "docker-compose.prod.yml")
        content = open(path, encoding="utf-8").read()
        # Should not use generic nginx:alpine or nginx:latest
        assert "nginx:1.25" in content
