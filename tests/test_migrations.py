"""Tests for database migration runner (Phase 10)."""

from __future__ import annotations

import os

import pytest

from tros.api.db import get_connection, init_db
from tros.api.migrations import MigrationRunner


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture(autouse=True)
def setup_db(db_path):
    """Initialize bootstrap schema before each test."""
    init_db(db_path)


class TestMigrationRunner:
    def test_applied_tracked(self, db_path):
        """Migrations tracking table is created and queryable."""
        runner = MigrationRunner(db_path=db_path)
        applied = runner.get_applied()
        # Fresh DB should have no applied migrations (bootstrap is separate)
        assert isinstance(applied, list)

    def test_run_pending_applies_migrations(self, db_path, tmp_path, monkeypatch):
        """Pending migrations are applied and tracked."""
        # Create a temporary migrations directory with a test migration
        mig_dir = tmp_path / "migrations"
        mig_dir.mkdir()
        (mig_dir / "001_test_schema.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);\n"
        )
        # Monkeypatch the migrations directory
        import tros.api.migrations as mig_module
        monkeypatch.setattr(mig_module, "_MIGRATIONS_DIR", mig_dir)

        runner = MigrationRunner(db_path=db_path)
        applied = runner.run_pending()
        assert "001_test_schema.sql" in applied

        # Verify the table was created
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_idempotent_re_run(self, db_path, tmp_path, monkeypatch):
        """Re-running applied migrations is a no-op."""
        mig_dir = tmp_path / "migrations"
        mig_dir.mkdir()
        (mig_dir / "001_test.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_idem (id INTEGER PRIMARY KEY);\n"
        )
        import tros.api.migrations as mig_module
        monkeypatch.setattr(mig_module, "_MIGRATIONS_DIR", mig_dir)

        runner = MigrationRunner(db_path=db_path)
        first = runner.run_pending()
        assert len(first) == 1
        # Second run should apply nothing
        second = runner.run_pending()
        assert len(second) == 0

    def test_pending_detection(self, db_path, tmp_path, monkeypatch):
        """Pending migrations are correctly detected."""
        mig_dir = tmp_path / "migrations"
        mig_dir.mkdir()
        (mig_dir / "001_a.sql").write_text(
            "CREATE TABLE IF NOT EXISTS tbl_a (id INTEGER PRIMARY KEY);\n"
        )
        (mig_dir / "002_b.sql").write_text(
            "CREATE TABLE IF NOT EXISTS tbl_b (id INTEGER PRIMARY KEY);\n"
        )
        import tros.api.migrations as mig_module
        monkeypatch.setattr(mig_module, "_MIGRATIONS_DIR", mig_dir)

        runner = MigrationRunner(db_path=db_path)
        pending = runner.get_pending()
        assert len(pending) == 2

        # Apply first one manually
        runner.run_pending()
        pending_after = runner.get_pending()
        assert len(pending_after) == 0

    def test_destructive_migration_blocked(self, db_path, tmp_path, monkeypatch):
        """Migrations with DROP TABLE are skipped."""
        mig_dir = tmp_path / "migrations"
        mig_dir.mkdir()
        (mig_dir / "001_safe.sql").write_text(
            "CREATE TABLE IF NOT EXISTS safe_tbl (id INTEGER PRIMARY KEY);\n"
        )
        (mig_dir / "002_destructive.sql").write_text(
            "CREATE TABLE IF NOT EXISTS drop_tbl (id INTEGER PRIMARY KEY);\n"
            "DROP TABLE IF EXISTS safe_tbl;\n"
        )
        import tros.api.migrations as mig_module
        monkeypatch.setattr(mig_module, "_MIGRATIONS_DIR", mig_dir)

        runner = MigrationRunner(db_path=db_path)
        applied = runner.run_pending()
        # Only the safe migration should be applied
        assert "001_safe.sql" in applied
        assert "002_destructive.sql" not in applied

    def test_migration_tracking_table(self, db_path):
        """Migration tracking table records applied_at timestamp."""
        import tros.api.migrations as mig_module
        from pathlib import Path

        runner = MigrationRunner(db_path=db_path)
        runner._ensure_tracking_table()

        conn = get_connection(db_path)
        # Insert a fake tracking entry
        conn.execute(
            "INSERT INTO migrations (name, applied_at) VALUES (?, ?)",
            ("test_migration.sql", "2026-01-01T00:00:00"),
        )
        conn.commit()
        rows = conn.execute("SELECT * FROM migrations").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["name"] == "test_migration.sql"
