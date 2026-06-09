from __future__ import annotations

import json
import time
from pathlib import Path

from .config import PROJECT_ROOT
from .context_window import ContextWindow


SESSION_STATE_PATH = PROJECT_ROOT / "session_state.json"


def load_session_state(path: Path = SESSION_STATE_PATH) -> ContextWindow:
    """Load persisted ReAct context window state.

    Args:
        path: Session state JSON path.

    Returns:
        ContextWindow with recent tool observations.
    """

    if not path.exists():
        return ContextWindow()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ContextWindow()
    return ContextWindow.deserialize(data.get("context_window", {}))


def session_state_snapshot(path: Path = SESSION_STATE_PATH) -> dict[str, object]:
    """Return persisted context-window state with metadata.

    Args:
        path: Session state JSON path.

    Returns:
        JSON-compatible state snapshot.
    """

    if not path.exists():
        return {"updated_at": None, "context_window": ContextWindow().serialize()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"updated_at": None, "context_window": ContextWindow().serialize(), "error": "unreadable session state"}
    return {
        "updated_at": data.get("updated_at"),
        "context_window": ContextWindow.deserialize(data.get("context_window", {})).serialize(),
    }


def session_state_stats(path: Path = SESSION_STATE_PATH) -> dict[str, object]:
    """Return compact telemetry for the persisted context window."""

    snapshot = session_state_snapshot(path=path)
    items = snapshot.get("context_window", {}).get("items", [])
    total_chars = sum(len(str(item.get("content", ""))) for item in items if isinstance(item, dict))
    tools: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool", "unknown"))
        tools[tool] = tools.get(tool, 0) + 1
    return {
        "updated_at": snapshot.get("updated_at"),
        "item_count": len(items),
        "content_chars": total_chars,
        "tools": tools,
        "has_error": bool(snapshot.get("error")),
    }


def save_session_state(context_window: ContextWindow, path: Path = SESSION_STATE_PATH) -> None:
    """Persist ReAct context window state to disk.

    Args:
        context_window: ContextWindow to persist.
        path: Session state JSON path.

    Returns:
        None.
    """

    payload = {
        "updated_at": int(time.time()),
        "context_window": context_window.serialize(),
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        return


def clear_session_state(path: Path = SESSION_STATE_PATH) -> None:
    """Clear persisted ReAct context-window state.

    Args:
        path: Session state JSON path.

    Returns:
        None.
    """

    save_session_state(ContextWindow(), path=path)


def prune_session_state(keep: int = 8, path: Path = SESSION_STATE_PATH) -> dict[str, object]:
    """Prune persisted context-window observations while preserving newest items."""

    window = load_session_state(path=path)
    result = window.prune(keep=keep)
    save_session_state(window, path=path)
    return result | {"context_window": window.serialize()}
