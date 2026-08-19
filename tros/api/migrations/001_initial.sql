-- Migration 001: Initial schema (Phase 10)
-- Creates core tables for execution tracking, mission results,
-- event replay, and idempotency key storage.

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
