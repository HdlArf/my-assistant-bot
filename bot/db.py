"""SQLite database layer for notes and users."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from bot.config import config


def _ensure_data_dir() -> None:
    """Create the data directory if it does not exist."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Provide a managed SQLite connection."""
    _ensure_data_dir()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notes_user
            ON notes (user_id)
            """
        )


def add_note(user_id: int, content: str) -> int:
    """Insert a new note and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (user_id, content) VALUES (?, ?)",
            (user_id, content),
        )
        return cursor.lastrowid


def list_notes(user_id: int) -> list[sqlite3.Row]:
    """Return all notes belonging to a user."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, content, created_at FROM notes "
            "WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return cursor.fetchall()


def delete_note(user_id: int, note_id: int) -> bool:
    """Delete a note by id. Return True if a row was removed."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )
        return cursor.rowcount > 0


def count_notes(user_id: int) -> int:
    """Return the number of notes for a user."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) AS total FROM notes WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return int(row["total"]) if row else 0
