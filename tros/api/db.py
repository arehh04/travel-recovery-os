"""SQLite database connection management (Phase 10).

Provides:
- get_db_path() — resolves database file path from settings
- get_connection() — returns a new WAL-mode SQLite connection
- init_db() — creates tables via the migration system
- Thread-safe via connection-per-operation pattern
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from tros.api.settings import get_settings

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Return the database file path from settings.

    Creates the parent directory if it doesn't exist.
    """
    settings = get_settings()
    db_path = settings.database_url
    # Ensure parent directory exists
    parent = Path(db_path).parent
    if parent != Path(".") and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and safe defaults.

    Each call returns a fresh connection — safe for multi-threaded use.
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create all required tables if they don't exist.

    This is a lightweight bootstrap — the full migration system
    (tros.api.migrations) handles schema evolution.
    """
    path = db_path or get_db_path()
    # Ensure parent directory exists
    parent = Path(path).parent
    if str(parent) != "." and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)
    try:
        conn.executescript(_INIT_SCHEMA)
        conn.commit()
        logger.info("Database initialized at %s", path)
    finally:
        conn.close()


# Minimal bootstrap schema — full migrations handled by MigrationRunner
_INIT_SCHEMA = """\
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    phase TEXT NOT NULL DEFAULT '',
    progress REAL NOT NULL DEFAULT 0.0,
    submitted_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    result_json TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_mission ON events(mission_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
