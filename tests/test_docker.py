"""Tests for Phase 9 Docker & deployment hardening."""

import os
import yaml

import pytest


class TestDockerfile:
    def test_has_non_root_user(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "useradd" in content or "adduser" in content
        assert "USER" in content
        # Non-root user should not be root
        assert "USER appuser" in content or "USER nonroot" in content

    def test_no_cache_dir_pip(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "--no-cache-dir" in content

    def test_stopsignal(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "STOPSIGNAL" in content


class TestNginxConfig:
    def test_nginx_conf_exists(self):
        assert os.path.isfile("nginx.conf")

    def test_sse_support(self):
        with open("nginx.conf") as f:
            content = f.read()
        assert "proxy_buffering off" in content
        assert "X-Accel-Buffering" in content

    def test_security_headers(self):
        with open("nginx.conf") as f:
            content = f.read()
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content
        assert "Strict-Transport-Security" in content

    def test_request_size_limit(self):
        with open("nginx.conf") as f:
            content = f.read()
        assert "client_max_body_size" in content


class TestDockerComposeProd:
    def test_valid_yaml(self):
        with open("docker-compose.prod.yml") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "services" in data

    def test_has_nginx_service(self):
        with open("docker-compose.prod.yml") as f:
            data = yaml.safe_load(f)
        assert "nginx" in data["services"]

    def test_has_api_service(self):
        with open("docker-compose.prod.yml") as f:
            data = yaml.safe_load(f)
        assert "tros-api" in data["services"]

    def test_healthcheck(self):
        with open("docker-compose.prod.yml") as f:
            data = yaml.safe_load(f)
        assert "healthcheck" in data["services"]["tros-api"]
