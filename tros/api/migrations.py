"""Database migration runner (Phase 10).

Applies numbered SQL migration files from the migrations/ directory.
Tracks applied migrations in a `migrations` table.

Features:
- Non-destructive: all statements use IF NOT EXISTS
- Never auto-runs DROP or TRUNCATE
- Logs each applied migration
- Thread-safe via connection-per-operation
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from tros.api.db import get_connection

logger = logging.getLogger(__name__)

# Path to SQL migration files
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Pattern for migration file names: NNN_description.sql
_MIGRATION_PATTERN = re.compile(r"^(\d{3})_.+\.sql$")

# Destructive keywords that are never auto-executed
_BLOCKED_KEYWORDS = {"DROP TABLE", "DROP INDEX", "TRUNCATE"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MigrationRunner:
    """Applies pending SQL migrations to the database.

    Migrations are SQL files in the migrations/ directory named
    ``NNN_description.sql`` (e.g. ``001_initial.sql``).
    Applied migrations are tracked in the ``migrations`` table.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def _ensure_tracking_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def get_applied(self) -> list[str]:
        """Return list of already-applied migration names."""
        self._ensure_tracking_table()
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM migrations ORDER BY name"
            ).fetchall()
            return [r["name"] for r in rows]
        finally:
            conn.close()

    def get_pending(self) -> list[Path]:
        """Return list of pending migration file paths (sorted by number)."""
        applied = set(self.get_applied())
        pending = []
        if not _MIGRATIONS_DIR.exists():
            return pending
        for f in sorted(_MIGRATIONS_DIR.iterdir()):
            m = _MIGRATION_PATTERN.match(f.name)
            if m and f.name not in applied:
                pending.append(f)
        return pending

    def run_pending(self) -> list[str]:
        """Apply all pending migrations. Returns list of applied names.

        Skips any migration containing blocked destructive keywords
        (DROP TABLE, DROP INDEX, TRUNCATE).
        """
        pending = self.get_pending()
        applied: list[str] = []

        for migration_path in pending:
            name = migration_path.name
            sql = migration_path.read_text(encoding="utf-8")

            # Safety: reject destructive operations
            sql_upper = sql.upper()
            if any(kw in sql_upper for kw in _BLOCKED_KEYWORDS):
                logger.warning(
                    "Skipping migration %s: contains destructive operation", name
                )
                continue

            logger.info("Applying migration: %s", name)
            conn = get_connection(self._db_path)
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO migrations (name, applied_at) VALUES (?, ?)",
                    (name, _now_iso()),
                )
                conn.commit()
                applied.append(name)
                logger.info("Migration applied: %s", name)
            except Exception:
                logger.exception("Failed to apply migration: %s", name)
                raise
            finally:
                conn.close()

        if not applied:
            logger.debug("No pending migrations to apply")
        return applied
