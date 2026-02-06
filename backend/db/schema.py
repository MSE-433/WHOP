"""SQL schema for the WHOP database."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    game_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active',
    round_number INTEGER NOT NULL DEFAULT 1,
    current_step TEXT NOT NULL DEFAULT 'event'
);

CREATE TABLE IF NOT EXISTS state_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES sessions(game_id),
    round_number INTEGER NOT NULL,
    step TEXT NOT NULL,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES sessions(game_id),
    round_number INTEGER NOT NULL,
    step TEXT NOT NULL,
    action_json TEXT NOT NULL,
    result TEXT NOT NULL DEFAULT 'ok',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_snapshots_game ON state_snapshots(game_id);
CREATE INDEX IF NOT EXISTS idx_actions_game ON actions(game_id);
"""
