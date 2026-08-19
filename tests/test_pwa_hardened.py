"""Tests for PWA hardening (Phase 10)."""

from __future__ import annotations

import json
import os

import pytest


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_file(rel_path: str) -> str:
    path = os.path.join(_ROOT, rel_path)
    return open(path, encoding="utf-8").read()


class TestSourceMaps:
    def test_sourcemap_hidden_in_vite_config(self):
        """Source maps are set to 'hidden' in vite config."""
        content = _read_file("frontend/vite.config.ts")
        assert "sourcemap: 'hidden'" in content or 'sourcemap: "hidden"' in content


class TestServiceWorkerCaching:
    def test_sw_caches_api_responses(self):
        """Service worker caches successful API responses (non-no-store)."""
        content = _read_file("frontend/public/sw.js")
        # Should have cache.put for API responses
        assert "cache.put(request, clone)" in content
        assert "response.ok" in content

    def test_sw_respects_no_store(self):
        """Service worker respects Cache-Control: no-store."""
        content = _read_file("frontend/public/sw.js")
        assert "no-store" in content

    def test_sw_version_bumped(self):
        """Service worker cache version bumped to v3."""
        content = _read_file("frontend/public/sw.js")
        assert "tros-v3" in content


class TestManifest:
    def test_manifest_has_required_fields(self):
        """Manifest has required PWA fields."""
        content = _read_file("frontend/public/manifest.json")
        data = json.loads(content)
        assert "name" in data
        assert "short_name" in data
        assert "start_url" in data
        assert "display" in data
        assert "categories" in data
        assert "lang" in data
        assert "scope" in data
        assert "id" in data

    def test_manifest_categories(self):
        """Manifest includes travel and productivity categories."""
        content = _read_file("frontend/public/manifest.json")
        data = json.loads(content)
        assert "travel" in data["categories"]
        assert "productivity" in data["categories"]


class TestIndexHTML:
    def test_apple_meta_tags(self):
        """index.html has Apple-specific meta tags."""
        content = _read_file("frontend/index.html")
        assert "apple-mobile-web-app-capable" in content
        assert "apple-mobile-web-app-status-bar-style" in content

    def test_no_user_scalable_no(self):
        """index.html does not disable user scaling (accessibility)."""
        content = _read_file("frontend/index.html")
        assert "user-scalable=no" not in content

    def test_version_meta_tag(self):
        """index.html has version meta tag."""
        content = _read_file("frontend/index.html")
        assert 'name="version"' in content


class TestFooterUpdate:
    def test_footer_updated(self):
        """App footer references Phase 10."""
        content = _read_file("frontend/src/App.tsx")
        assert "Phase 10" in content
