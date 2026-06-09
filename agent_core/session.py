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
