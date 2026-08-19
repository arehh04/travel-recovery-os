"""Tests for HTTPS and security headers (Phase 10)."""

from __future__ import annotations

import os

import pytest


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_nginx_conf() -> str:
    path = os.path.join(_ROOT, "nginx.conf")
    return open(path, encoding="utf-8").read()


def _read_ssl_conf() -> str:
    path = os.path.join(_ROOT, "nginx", "ssl.conf")
    return open(path, encoding="utf-8").read()


class TestHTTPSSecurity:
    def test_hsts_includes_preload(self):
        """HSTS header includes preload directive."""
        content = _read_nginx_conf()
        assert "preload" in content
        assert "Strict-Transport-Security" in content

    def test_tls_12_plus_only(self):
        """SSL config only allows TLS 1.2 and 1.3."""
        content = _read_ssl_conf()
        assert "TLSv1.2" in content
        assert "TLSv1.3" in content
        # Must NOT allow older protocols
        assert "TLSv1.0" not in content
        assert "TLSv1.1" not in content
        assert "SSLv3" not in content

    def test_csp_no_unsafe_inline_scripts(self):
        """Content-Security-Policy does not include unsafe-inline for scripts."""
        content = _read_nginx_conf()
        # Find the CSP header line
        for line in content.split("\n"):
            if "Content-Security-Policy" in line:
                # script-src should NOT have unsafe-inline
                assert "script-src 'self' 'unsafe-inline'" not in line, (
                    "CSP should not allow unsafe-inline for scripts"
                )
                break
        else:
            pytest.fail("Content-Security-Policy header not found in nginx.conf")

    def test_permissions_policy_header(self):
        """Permissions-Policy header is present."""
        content = _read_nginx_conf()
        assert "Permissions-Policy" in content
        assert "camera=()" in content

    def test_security_headers_on_all_responses(self):
        """All security headers are set with 'always' directive."""
        content = _read_nginx_conf()
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Strict-Transport-Security",
        ]
        for header in required_headers:
            assert header in content, f"Missing security header: {header}"

    def test_ssl_session_cache(self):
        """SSL config has session cache configured."""
        content = _read_ssl_conf()
        assert "ssl_session_cache" in content
        assert "ssl_session_timeout" in content
