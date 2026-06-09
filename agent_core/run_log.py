from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .agent import AgentRun
from .config import PROJECT_ROOT


RUN_LOG_PATH = PROJECT_ROOT / "data" / "run_log.sqlite3"


def connect(path: Path = RUN_LOG_PATH) -> sqlite3.Connection:
    """Open the run log database and ensure tables exist.

    Args:
        path: SQLite database path.

    Returns:
        sqlite3 connection with run log schema.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            provider TEXT NOT NULL,
            tools_used TEXT NOT NULL,
            react_steps TEXT NOT NULL,
            provider_attempts TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            fallback_used INTEGER NOT NULL,
            error TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id, id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id)")
    return con


def add_run(session_id: str, prompt: str, run: AgentRun) -> None:
    """Persist an agent run for audit/debugging.

    Args:
        session_id: Browser/session id.
        prompt: User prompt.
        run: AgentRun metadata.

    Returns:
        None.
    """

    con = connect()
    con.execute(
        """
        INSERT INTO runs(
            run_id, session_id, prompt, provider, tools_used, react_steps,
            provider_attempts, duration_ms, fallback_used, error, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run.run_id,
            session_id,
            prompt,
            run.provider,
            json.dumps(run.tools_used),
            json.dumps(run.react_steps),
            json.dumps(run.provider_attempts),
            run.duration_ms,
            1 if run.fallback_used else 0,
            run.error,
            int(time.time()),
        ),
    )
    con.commit()
    con.close()


def recent_runs(session_id: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """Fetch recent agent run metadata.

    Args:
        session_id: Optional session filter.
        limit: Maximum rows.

    Returns:
        List of run dictionaries.
    """

    con = connect()
    if session_id:
        rows = con.execute(
            """
            SELECT run_id, session_id, prompt, provider, tools_used, react_steps,
                   provider_attempts, duration_ms, fallback_used, error, created_at
            FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT run_id, session_id, prompt, provider, tools_used, react_steps,
                   provider_attempts, duration_ms, fallback_used, error, created_at
            FROM runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [row_to_dict(row) for row in rows]


def row_to_dict(row: tuple[object, ...]) -> dict[str, object]:
    """Convert a SQLite run row to JSON-compatible data.

    Args:
        row: SQLite row tuple.

    Returns:
        Dictionary run metadata.
    """

    return {
        "run_id": row[0],
        "session_id": row[1],
        "prompt": row[2],
        "provider": row[3],
        "tools_used": json.loads(row[4]),
        "react_steps": json.loads(row[5]),
        "provider_attempts": json.loads(row[6]),
        "duration_ms": row[7],
        "fallback_used": bool(row[8]),
        "error": row[9],
        "created_at": row[10],
    }


def clear_runs(session_id: str | None = None) -> None:
    """Clear run log entries.

    Args:
        session_id: Optional session filter.

    Returns:
        None.
    """

    con = connect()
    if session_id:
        con.execute("DELETE FROM runs WHERE session_id = ?", (session_id,))
    else:
        con.execute("DELETE FROM runs")
    con.commit()
    con.close()
