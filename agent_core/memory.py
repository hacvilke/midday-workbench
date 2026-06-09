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
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS session_summaries (
            session_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
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
    con.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
    con.commit()
    con.close()


def prune_messages(session_id: str, keep: int = 100) -> dict[str, object]:
    """Prune raw chat messages while preserving the condensed summary."""

    keep = max(1, int(keep))
    con = connect()
    before = con.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    con.execute(
        """
        DELETE FROM messages
        WHERE session_id = ?
          AND id NOT IN (
            SELECT id FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
          )
        """,
        (session_id, session_id, keep),
    )
    con.commit()
    after = con.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    con.close()
    return {
        "session_id": session_id,
        "keep": keep,
        "deleted": max(0, int(before) - int(after)),
        "remaining": int(after),
        "summary_preserved": bool(get_session_summary(session_id).get("summary")),
    }


def get_session_summary(session_id: str) -> dict[str, object]:
    """Fetch the condensed session memory summary.

    Args:
        session_id: Browser/session id.

    Returns:
        Summary payload with text and timestamp, or an empty summary.
    """

    con = connect()
    row = con.execute(
        "SELECT summary, updated_at FROM session_summaries WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    con.close()
    if not row:
        return {"summary": "", "updated_at": None}
    return {"summary": row[0], "updated_at": row[1]}


def memory_stats(session_id: str | None = None) -> dict[str, object]:
    """Return compact memory telemetry for control-plane and metrics APIs."""

    con = connect()
    if session_id:
        message_count = con.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        summary_row = con.execute(
            "SELECT summary, updated_at FROM session_summaries WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        session_count = 1 if message_count or summary_row else 0
    else:
        message_count = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        summary_row = con.execute(
            "SELECT summary, updated_at FROM session_summaries ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        session_count = con.execute(
            "SELECT COUNT(DISTINCT session_id) FROM messages"
        ).fetchone()[0]
    con.close()

    summary = summary_row[0] if summary_row else ""
    updated_at = summary_row[1] if summary_row else None
    return {
        "session_id": session_id,
        "message_count": int(message_count),
        "session_count": int(session_count),
        "has_summary": bool(summary),
        "summary_chars": len(str(summary)),
        "summary_updated_at": updated_at,
    }


def update_session_summary(session_id: str, user_message: str, agent_answer: str) -> dict[str, object]:
    """Update deterministic condensed memory for a session.

    This is intentionally model-free: it keeps durable facts about recent user
    requests, tools, and outcomes without storing huge transcripts in prompts.

    Args:
        session_id: Browser/session id.
        user_message: Latest user prompt.
        agent_answer: Latest agent answer.

    Returns:
        Updated summary payload.
    """

    previous = str(get_session_summary(session_id).get("summary") or "")
    bullets = [line.strip("- ").strip() for line in previous.splitlines() if line.strip()]
    new_fact = summarize_exchange(user_message, agent_answer)
    if new_fact:
        bullets.append(new_fact)
    compact = []
    for bullet in bullets[-8:]:
        if bullet and bullet not in compact:
            compact.append(bullet[:220])
    summary = "\n".join(f"- {bullet}" for bullet in compact)
    now = int(time.time())
    con = connect()
    con.execute(
        """
        INSERT INTO session_summaries(session_id, summary, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET summary = excluded.summary, updated_at = excluded.updated_at
        """,
        (session_id, summary, now),
    )
    con.commit()
    con.close()
    return {"summary": summary, "updated_at": now}


def summarize_exchange(user_message: str, agent_answer: str) -> str:
    """Create one compact memory bullet from an exchange.

    Args:
        user_message: Latest user prompt.
        agent_answer: Latest agent answer.

    Returns:
        A short durable memory bullet.
    """

    prompt = " ".join(user_message.split())[:120]
    answer = " ".join(agent_answer.split())[:120]
    if not prompt:
        return ""
    if answer.startswith("```mermaid"):
        outcome = "returned a visual Mermaid response"
    elif "Provider failed" in answer:
        outcome = "used local fallback after provider failure"
    else:
        outcome = answer
    return f"User asked: {prompt}; outcome: {outcome}"
