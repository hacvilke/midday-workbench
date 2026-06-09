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
            plan TEXT DEFAULT '{}',
            file_writes TEXT DEFAULT '[]',
            usage TEXT DEFAULT '{}'
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
    try:
        con.execute("ALTER TABLE runs ADD COLUMN file_writes TEXT DEFAULT '[]'")
        con.commit()
    except sqlite3.OperationalError:
        pass  # Column already present
    try:
        con.execute("ALTER TABLE runs ADD COLUMN usage TEXT DEFAULT '{}'")
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
            policy_decision TEXT DEFAULT '{}',
            duration_ms INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    try:
        con.execute("ALTER TABLE command_runs ADD COLUMN policy_decision TEXT DEFAULT '{}'")
        con.commit()
    except sqlite3.OperationalError:
        pass  # Column already present
    con.execute("CREATE INDEX IF NOT EXISTS idx_command_runs_session ON command_runs(session_id, id)")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS file_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            action TEXT NOT NULL,
            path TEXT NOT NULL,
            bytes_written INTEGER NOT NULL,
            lines INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            created INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_file_events_session ON file_events(session_id, id)")
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
            verifier_reports, plan, file_writes, usage
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(run.file_writes or []),
            json.dumps(run.usage or {}),
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
                   verifier_reports, plan, file_writes, usage
            FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT run_id, session_id, prompt, provider, tools_used, react_steps,
                   provider_attempts, duration_ms, fallback_used, error, created_at,
                   verifier_reports, plan, file_writes, usage
            FROM runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [row_to_dict(row) for row in rows]


def get_run(run_id: str) -> dict[str, object] | None:
    """Fetch one run by id.

    Args:
        run_id: Run identifier.

    Returns:
        Run dictionary, or None if it does not exist.
    """

    con = connect()
    row = con.execute(
        """
        SELECT run_id, session_id, prompt, provider, tools_used, react_steps,
               provider_attempts, duration_ms, fallback_used, error, created_at,
               verifier_reports, plan, file_writes, usage
        FROM runs WHERE run_id = ? ORDER BY id DESC LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    con.close()
    return row_to_dict(row) if row else None


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
        "file_writes": json.loads(row[13]) if len(row) > 13 and row[13] else [],
        "usage": json.loads(row[14]) if len(row) > 14 and row[14] else {},
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
    policy_decision: dict[str, object] | None = None,
) -> None:
    """Persist a sandbox command run for auditability.

    Args:
        session_id: Browser/session id.
        command: Command string requested.
        exit_code: Process exit code.
        output: Combined output.
        verified: Verifier report payload.
        duration_ms: Execution duration in milliseconds.
        policy_decision: Optional structured sandbox decision payload.

    Returns:
        None.
    """

    con = connect()
    con.execute(
        """
        INSERT INTO command_runs(session_id, command, exit_code, output, verified, policy_decision, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            command,
            exit_code,
            output[:8000],
            json.dumps(verified),
            json.dumps(policy_decision or {}),
            duration_ms,
            int(time.time()),
        ),
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
            SELECT session_id, command, exit_code, output, verified, policy_decision, duration_ms, created_at
            FROM command_runs WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT session_id, command, exit_code, output, verified, policy_decision, duration_ms, created_at
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
            "policy_decision": json.loads(row[5]) if row[5] else {},
            "duration_ms": row[6],
            "created_at": row[7],
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


def add_file_event(
    session_id: str,
    action: str,
    write: dict[str, object],
) -> None:
    """Persist a file mutation event for auditability."""

    con = connect()
    con.execute(
        """
        INSERT INTO file_events(
            session_id, action, path, bytes_written, lines, sha256,
            created, message, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            action,
            str(write.get("path", ""))[:500],
            int(write.get("bytes_written") or 0),
            int(write.get("lines") or 0),
            str(write.get("sha256", "")),
            1 if write.get("created") else 0,
            str(write.get("message", ""))[:1000],
            int(time.time()),
        ),
    )
    con.commit()
    con.close()


def recent_file_events(session_id: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """Fetch recent file mutation events."""

    con = connect()
    if session_id:
        rows = con.execute(
            """
            SELECT session_id, action, path, bytes_written, lines, sha256, created, message, created_at
            FROM file_events WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT session_id, action, path, bytes_written, lines, sha256, created, message, created_at
            FROM file_events ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    con.close()
    return [
        {
            "session_id": row[0],
            "action": row[1],
            "path": row[2],
            "bytes_written": row[3],
            "lines": row[4],
            "sha256": row[5],
            "created": bool(row[6]),
            "message": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


def clear_file_events(session_id: str | None = None) -> None:
    """Clear file mutation audit events."""

    con = connect()
    if session_id:
        con.execute("DELETE FROM file_events WHERE session_id = ?", (session_id,))
    else:
        con.execute("DELETE FROM file_events")
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


def retention_stats(session_id: str | None = None) -> dict[str, object]:
    """Return audit-log row counts for retention visibility."""

    con = connect()
    if session_id:
        counts = {
            "runs": _count_where(con, "runs", session_id),
            "commands": _count_where(con, "command_runs", session_id),
            "files": _count_where(con, "file_events", session_id),
            "decisions": _count_where(con, "decisions", session_id),
        }
    else:
        counts = {
            "runs": _count_all(con, "runs"),
            "commands": _count_all(con, "command_runs"),
            "files": _count_all(con, "file_events"),
            "decisions": _count_all(con, "decisions"),
        }
    con.close()
    return {
        "session_id": session_id,
        "counts": counts,
        "total": sum(int(value) for value in counts.values()),
    }


def prune_history(session_id: str | None = None, keep_per_table: int = 500) -> dict[str, object]:
    """Prune old audit rows while keeping the newest rows per table."""

    keep = max(0, int(keep_per_table))
    con = connect()
    deleted = {
        "runs": _prune_table(con, "runs", session_id, keep),
        "commands": _prune_table(con, "command_runs", session_id, keep),
        "files": _prune_table(con, "file_events", session_id, keep),
        "decisions": _prune_table(con, "decisions", session_id, keep),
    }
    con.commit()
    con.execute("VACUUM")
    con.close()
    return {
        "session_id": session_id,
        "keep_per_table": keep,
        "deleted": deleted,
        "deleted_total": sum(int(value) for value in deleted.values()),
    }


def _count_all(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_where(con: sqlite3.Connection, table: str, session_id: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table} WHERE session_id = ?", (session_id,)).fetchone()[0])


def _prune_table(con: sqlite3.Connection, table: str, session_id: str | None, keep: int) -> int:
    before = _count_where(con, table, session_id) if session_id else _count_all(con, table)
    if session_id:
        con.execute(
            f"""
            DELETE FROM {table}
            WHERE session_id = ?
              AND id NOT IN (
                SELECT id FROM {table}
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
              )
            """,
            (session_id, session_id, keep),
        )
        after = _count_where(con, table, session_id)
    else:
        con.execute(
            f"""
            DELETE FROM {table}
            WHERE id NOT IN (
                SELECT id FROM {table}
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (keep,),
        )
        after = _count_all(con, table)
    return max(0, before - after)


def operational_metrics(session_id: str | None = None) -> dict[str, object]:
    """Summarize operational telemetry for runs, commands, and decisions.

    Args:
        session_id: Optional session filter.

    Returns:
        JSON-compatible metrics payload.
    """

    runs = recent_runs(session_id=session_id, limit=500)
    commands = recent_command_runs(session_id=session_id, limit=500)
    file_events = recent_file_events(session_id=session_id, limit=500)
    decisions = recent_decisions(session_id=session_id, limit=500)
    provider_counts: dict[str, int] = {}
    tool_counts: dict[str, int] = {}
    verifier_total = 0
    verifier_passed = 0
    fallback_count = 0
    total_duration = 0
    total_prompt_chars = 0
    total_answer_chars = 0
    total_context_chars = 0
    ambiguous_routes = 0
    low_confidence_routes = 0
    provider_route_reports = 0
    provider_route_failed = 0
    provider_route_degraded = 0

    for run in runs:
        provider = str(run.get("provider", "unknown"))
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        total_duration += int(run.get("duration_ms") or 0)
        usage = run.get("usage") or {}
        total_prompt_chars += int(usage.get("prompt_chars") or 0)
        total_answer_chars += int(usage.get("answer_chars") or 0)
        total_context_chars += int(usage.get("context_chars") or 0)
        if run.get("fallback_used"):
            fallback_count += 1
        plan = run.get("plan") or {}
        confidence = plan.get("confidence")
        if plan.get("ambiguous"):
            ambiguous_routes += 1
        if isinstance(confidence, (int, float)) and confidence < 0.75:
            low_confidence_routes += 1
        tools = run.get("tools_used") or []
        for tool in tools:
            name = str(tool)
            tool_counts[name] = tool_counts.get(name, 0) + 1
        for report in run.get("verifier_reports") or []:
            verifier_total += 1
            if report.get("passed"):
                verifier_passed += 1
            if report.get("action") == "provider_route":
                provider_route_reports += 1
                if not report.get("passed"):
                    provider_route_failed += 1
                summary = str(report.get("summary") or "")
                if "failed=" in summary and "failed=none" not in summary:
                    provider_route_degraded += 1

    command_failures = sum(1 for command in commands if int(command.get("exit_code") or 0) != 0)
    decision_counts: dict[str, int] = {}
    for decision in decisions:
        kind = str(decision.get("kind", "unknown"))
        decision_counts[kind] = decision_counts.get(kind, 0) + 1

    return {
        "session_id": session_id,
        "retention": retention_stats(session_id=session_id),
        "runs": {
            "count": len(runs),
            "fallback_count": fallback_count,
            "ambiguous_routes": ambiguous_routes,
            "low_confidence_routes": low_confidence_routes,
            "average_duration_ms": int(total_duration / len(runs)) if runs else 0,
            "providers": provider_counts,
            "tools": tool_counts,
        },
        "usage": {
            "average_prompt_chars": int(total_prompt_chars / len(runs)) if runs else 0,
            "average_answer_chars": int(total_answer_chars / len(runs)) if runs else 0,
            "average_context_chars": int(total_context_chars / len(runs)) if runs else 0,
        },
        "verifier": {
            "count": verifier_total,
            "passed": verifier_passed,
            "failed": max(0, verifier_total - verifier_passed),
            "pass_rate": round(verifier_passed / verifier_total, 3) if verifier_total else None,
        },
        "provider_routes": {
            "count": provider_route_reports,
            "failed": provider_route_failed,
            "degraded": provider_route_degraded,
        },
        "commands": {
            "count": len(commands),
            "failures": command_failures,
            "successes": max(0, len(commands) - command_failures),
        },
        "files": {
            "count": len(file_events),
            "created": sum(1 for event in file_events if event.get("created")),
            "patched": sum(1 for event in file_events if event.get("action") == "patch"),
            "written": sum(1 for event in file_events if event.get("action") == "write"),
        },
        "decisions": {
            "count": len(decisions),
            "kinds": decision_counts,
        },
    }


def activity_timeline(session_id: str | None = None, limit: int = 30) -> list[dict[str, object]]:
    """Return a merged chronological activity stream.

    Args:
        session_id: Optional session filter.
        limit: Maximum timeline items.

    Returns:
        List of run, command, and decision events ordered newest first.
    """

    events: list[dict[str, object]] = []
    for run in recent_runs(session_id=session_id, limit=limit):
        events.append(
            {
                "type": "run",
                "id": run["run_id"],
                "session_id": run["session_id"],
                "title": str(run.get("prompt", ""))[:120],
                "summary": f"{run.get('provider')} · {len(run.get('tools_used') or [])} tool(s)",
                "status": "failed" if run.get("error") else "ok",
                "created_at": run["created_at"],
            }
        )
    for command in recent_command_runs(session_id=session_id, limit=limit):
        verified = command.get("verified") or {}
        events.append(
            {
                "type": "command",
                "id": command["command"],
                "session_id": command["session_id"],
                "title": command["command"],
                "summary": verified.get("summary", f"exit={command.get('exit_code')}"),
                "status": "ok" if int(command.get("exit_code") or 0) == 0 else "failed",
                "created_at": command["created_at"],
            }
        )
    for file_event in recent_file_events(session_id=session_id, limit=limit):
        events.append(
            {
                "type": "file",
                "id": file_event["path"],
                "session_id": file_event["session_id"],
                "title": f"{file_event.get('action')} {file_event.get('path')}",
                "summary": f"{file_event.get('bytes_written')} bytes - sha256 {str(file_event.get('sha256', ''))[:12]}",
                "status": "ok",
                "created_at": file_event["created_at"],
            }
        )
    for decision in recent_decisions(session_id=session_id, limit=limit):
        payload = decision.get("decision") or {}
        events.append(
            {
                "type": "decision",
                "id": decision["kind"],
                "session_id": decision["session_id"],
                "title": decision["input"],
                "summary": str(payload.get("intent") or payload.get("action_type") or decision["kind"]),
                "status": "ok",
                "created_at": decision["created_at"],
            }
        )
    return sorted(events, key=lambda item: int(item.get("created_at") or 0), reverse=True)[:limit]
