from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .config import PROJECT_ROOT


MEMORY_PATH = PROJECT_ROOT / "data" / "agent_memory.sqlite3"


def connect(path: Path = MEMORY_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
    return con


def add_message(session_id: str, role: str, content: str) -> None:
    con = connect()
    con.execute(
        "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, int(time.time())),
    )
    con.commit()
    con.close()


def get_recent_messages(session_id: str, limit: int = 8) -> list[dict[str, object]]:
    con = connect()
    rows = con.execute(
        "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    con.close()
    return [
        {"role": role, "content": content, "created_at": created_at}
        for role, content, created_at in reversed(rows)
    ]


def clear_session(session_id: str) -> None:
    con = connect()
    con.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    con.commit()
    con.close()
