"""Tests for CI/CD configuration (Phase 10)."""

from __future__ import annotations

import os

import pytest


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_file(rel_path: str) -> str:
    path = os.path.join(_ROOT, rel_path)
    return open(path, encoding="utf-8").read()


class TestCIWorkflow:
    def test_ci_workflow_exists(self):
        """CI workflow file exists."""
        path = os.path.join(_ROOT, ".github", "workflows", "ci.yml")
        assert os.path.exists(path)

    def test_ci_workflow_has_required_jobs(self):
        """CI workflow has all required jobs."""
        content = _read_file(".github/workflows/ci.yml")
        required_jobs = ["lint", "test-backend", "test-frontend", "build-frontend", "security-scan"]
        for job in required_jobs:
            assert job in content, f"CI workflow missing job: {job}"

    def test_ci_workflow_has_docker_build(self):
        """CI workflow includes docker build job."""
        content = _read_file(".github/workflows/ci.yml")
        assert "docker-build" in content or "Docker Build" in content


class TestDeployWorkflow:
    def test_deploy_workflow_exists(self):
        """Deploy workflow file exists."""
        path = os.path.join(_ROOT, ".github", "workflows", "deploy.yml")
        assert os.path.exists(path)

    def test_deploy_only_on_main(self):
        """Deploy workflow only triggers on main branch."""
        content = _read_file(".github/workflows/deploy.yml")
        assert "refs/heads/main" in content

    def test_no_hardcoded_secrets(self):
        """Workflow files do not hardcode secrets."""
        for wf in ["ci.yml", "deploy.yml"]:
            content = _read_file(f".github/workflows/{wf}")
            # Check no actual API keys are hardcoded (ignore grep patterns in scripts)
            import re
            # Look for actual key patterns (sk- followed by 20+ alphanumeric chars)
            keys = re.findall(r"sk-[a-zA-Z0-9]{20,}", content)
            assert not keys, f"Hardcoded API key in {wf}: {keys[0][:20]}..."
            # Secrets should use ${{ secrets.XXX }} pattern
            assert "${{ secrets." in content or "secrets" not in content.lower()
