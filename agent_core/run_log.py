"""Persistent run log for agent runs, with verifier report storage."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .agent import AgentRun
from .config import PROJECT_ROOT


RUN_LOG_PATH = PROJECT_ROOT / "data" / "run_log.sqlite3"


def connect(path: Path = RUN_LOG_PATH) -> sqlite3.Connection:
    """Open the run log database and ensure tables/columns exist.

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
            created_at INTEGER NOT NULL,
            verifier_reports TEXT DEFAULT '[]',
            plan TEXT DEFAULT '{}'
        )
        """
    )
    # Migrate: add verifier_reports column if this DB pre-dates it
    try:
        con.execute("ALTER TABLE runs ADD COLUMN verifier_reports TEXT DEFAULT '[]'")
        con.commit()
    except sqlite3.OperationalError:
        pass  # Column already present
    try:
        con.execute("ALTER TABLE runs ADD COLUMN plan TEXT DEFAULT '{}'")
        con.commit()
    except sqlite3.OperationalError:
        pass  # Column already present

    con.execute("CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id, id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id)")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS command_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            output TEXT NOT NULL,
            verified TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_command_runs_session ON command_runs(session_id, id)")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            input TEXT NOT NULL,
            decision TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id, id)")
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
            provider_attempts, duration_ms, fallback_used, error, created_at,
            verifier_reports, plan
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(run.verifier_reports),
            json.dumps(run.plan or {}),
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
                   provider_attempts, duration_ms, fallback_used, error, created_at,
                   verifier_reports, plan
            FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT run_id, session_id, prompt, provider, tools_used, react_steps,
                   provider_attempts, duration_ms, fallback_used, error, created_at,
                   verifier_reports, plan
            FROM runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [row_to_dict(row) for row in rows]


def get_sessions(limit: int = 50) -> list[dict[str, object]]:
    """Return unique sessions with their last-active time and run count.

    Args:
        limit: Maximum sessions to return.

    Returns:
        List of session summary dicts ordered by most recently active.
    """
    con = connect()
    rows = con.execute(
        """
        SELECT session_id, COUNT(*) AS run_count, MAX(created_at) AS last_active
        FROM runs
        GROUP BY session_id
        ORDER BY last_active DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    con.close()
    return [
        {"session_id": row[0], "run_count": row[1], "last_active": row[2]}
        for row in rows
    ]


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
        "verifier_reports": json.loads(row[11]) if len(row) > 11 and row[11] else [],
        "plan": json.loads(row[12]) if len(row) > 12 and row[12] else {},
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


def add_command_run(
    session_id: str,
    command: str,
    exit_code: int,
    output: str,
    verified: dict[str, object],
    duration_ms: int,
) -> None:
    """Persist a sandbox command run for auditability.

    Args:
        session_id: Browser/session id.
        command: Command string requested.
        exit_code: Process exit code.
        output: Combined output.
        verified: Verifier report payload.
        duration_ms: Execution duration in milliseconds.

    Returns:
        None.
    """

    con = connect()
    con.execute(
        """
        INSERT INTO command_runs(session_id, command, exit_code, output, verified, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, command, exit_code, output[:8000], json.dumps(verified), duration_ms, int(time.time())),
    )
    con.commit()
    con.close()


def recent_command_runs(session_id: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """Fetch recent sandbox command runs.

    Args:
        session_id: Optional session filter.
        limit: Maximum rows.

    Returns:
        List of command-run dictionaries.
    """

    con = connect()
    if session_id:
        rows = con.execute(
            """
            SELECT session_id, command, exit_code, output, verified, duration_ms, created_at
            FROM command_runs WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT session_id, command, exit_code, output, verified, duration_ms, created_at
            FROM command_runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [
        {
            "session_id": row[0],
            "command": row[1],
            "exit_code": row[2],
            "output": row[3],
            "verified": json.loads(row[4]),
            "duration_ms": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def clear_command_runs(session_id: str | None = None) -> None:
    """Clear sandbox command run history.

    Args:
        session_id: Optional session filter.

    Returns:
        None.
    """

    con = connect()
    if session_id:
        con.execute("DELETE FROM command_runs WHERE session_id = ?", (session_id,))
    else:
        con.execute("DELETE FROM command_runs")
    con.commit()
    con.close()


def add_decision(session_id: str, kind: str, input_text: str, decision: dict[str, object]) -> None:
    """Persist an autonomous control-plane decision.

    Args:
        session_id: Browser/session id.
        kind: Decision kind, such as route or policy.
        input_text: Prompt, action type, or command being evaluated.
        decision: JSON-compatible decision payload.

    Returns:
        None.
    """

    con = connect()
    con.execute(
        """
        INSERT INTO decisions(session_id, kind, input, decision, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, kind, input_text[:1000], json.dumps(decision), int(time.time())),
    )
    con.commit()
    con.close()


def recent_decisions(session_id: str | None = None, limit: int = 50) -> list[dict[str, object]]:
    """Fetch recent autonomous decisions.

    Args:
        session_id: Optional session filter.
        limit: Maximum rows.

    Returns:
        List of decision dictionaries.
    """

    con = connect()
    if session_id:
        rows = con.execute(
            """
            SELECT session_id, kind, input, decision, created_at
            FROM decisions WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT session_id, kind, input, decision, created_at
            FROM decisions ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [
        {
            "session_id": row[0],
            "kind": row[1],
            "input": row[2],
            "decision": json.loads(row[3]),
            "created_at": row[4],
        }
        for row in rows
    ]


def clear_decisions(session_id: str | None = None) -> None:
    """Clear autonomous decision history.

    Args:
        session_id: Optional session filter.

    Returns:
        None.
    """

    con = connect()
    if session_id:
        con.execute("DELETE FROM decisions WHERE session_id = ?", (session_id,))
    else:
        con.execute("DELETE FROM decisions")
    con.commit()
    con.close()
