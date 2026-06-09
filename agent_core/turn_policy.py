"""Per-turn policy helpers for routing and tool use."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnPolicy:
    """Compact policy decision for the latest user message."""

    mode: str
    block_tools: bool
    reason: str


NO_TOOLS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), reason)
    for pattern, reason in (
        (r"\bguide[-\s]?only\b", "guide-only mode requested"),
        (r"\bno[-\s]?tools?\b", "no-tools mode requested"),
        (r"\bdo not use (?:any )?tools?\b", "user forbids tool use"),
        (r"\bdon'?t use (?:any )?tools?\b", "user forbids tool use"),
        (r"\bwithout (?:using )?(?:any )?tools?\b", "user requested a no-tool answer"),
        (r"\banswer (?:directly|normally)\b", "direct answer requested"),
    )
)


def classify_turn_policy(message: object) -> TurnPolicy:
    """Classify the latest turn for hard tool-use constraints."""

    if not isinstance(message, str) or not message.strip():
        return TurnPolicy("normal", False, "normal turn")
    text = re.sub(r"\s+", " ", message.strip())
    for pattern, reason in NO_TOOLS_PATTERNS:
        if pattern.search(text):
            return TurnPolicy("guide_only", True, reason)
    return TurnPolicy("normal", False, "normal turn")
