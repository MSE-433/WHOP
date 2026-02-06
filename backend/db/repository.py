"""Data access layer for game sessions and state."""

import sqlite3
from datetime import datetime

from models.game_state import GameState


def create_session(conn: sqlite3.Connection, game_id: str, state: GameState) -> None:
    """Insert a new session and its initial state snapshot."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO sessions (game_id, created_at, updated_at, status, round_number, current_step) "
        "VALUES (?, ?, ?, 'active', ?, ?)",
        (game_id, now, now, state.round_number, state.current_step.value),
    )
    conn.execute(
        "INSERT INTO state_snapshots (game_id, round_number, step, state_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (game_id, state.round_number, state.current_step.value, state.model_dump_json(), now),
    )


def save_state(conn: sqlite3.Connection, state: GameState) -> None:
    """Save a new state snapshot and update session metadata."""
    now = datetime.utcnow().isoformat()
    status = "finished" if state.is_finished else "active"
    conn.execute(
        "UPDATE sessions SET updated_at=?, status=?, round_number=?, current_step=? WHERE game_id=?",
        (now, status, state.round_number, state.current_step.value, state.game_id),
    )
    conn.execute(
        "INSERT INTO state_snapshots (game_id, round_number, step, state_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (state.game_id, state.round_number, state.current_step.value, state.model_dump_json(), now),
    )


def load_state(conn: sqlite3.Connection, game_id: str) -> GameState | None:
    """Load the latest state snapshot for a game."""
    row = conn.execute(
        "SELECT state_json FROM state_snapshots WHERE game_id=? ORDER BY id DESC LIMIT 1",
        (game_id,),
    ).fetchone()
    if row is None:
        return None
    return GameState.model_validate_json(row["state_json"])


def log_action(
    conn: sqlite3.Connection,
    game_id: str,
    round_number: int,
    step: str,
    action_json: str,
    result: str = "ok",
    error_message: str | None = None,
) -> None:
    """Append an action to the audit log."""
    conn.execute(
        "INSERT INTO actions (game_id, round_number, step, action_json, result, error_message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (game_id, round_number, step, action_json, result, error_message, datetime.utcnow().isoformat()),
    )


def get_session(conn: sqlite3.Connection, game_id: str) -> dict | None:
    """Get session metadata."""
    row = conn.execute("SELECT * FROM sessions WHERE game_id=?", (game_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def list_sessions(conn: sqlite3.Connection) -> list[dict]:
    """List all sessions."""
    rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_round_snapshots(conn: sqlite3.Connection, game_id: str) -> list[GameState]:
    """Get one snapshot per completed round (the paperwork-step snapshot = end-of-round state).

    Returns GameState objects ordered by round number.
    """
    rows = conn.execute(
        "SELECT state_json FROM state_snapshots "
        "WHERE game_id=? AND step='paperwork' "
        "ORDER BY round_number ASC",
        (game_id,),
    ).fetchall()
    return [GameState.model_validate_json(row["state_json"]) for row in rows]
