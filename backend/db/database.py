"""SQLite database connection management."""

import sqlite3
from contextlib import contextmanager

from config import settings
from db.schema import SCHEMA_SQL

_db_path: str = settings.db_path


def set_db_path(path: str) -> None:
    """Override the database path (used by tests)."""
    global _db_path
    _db_path = path


@contextmanager
def get_db():
    """Yield a sqlite3 connection with auto-commit/rollback."""
    conn = sqlite3.connect(_db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
