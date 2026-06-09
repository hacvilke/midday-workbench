from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from .oss_tools import ToolResult


@dataclass(frozen=True)
class ContextItem:
    """Stores one tool observation for later tool chaining.

    Args:
        tool: Tool name.
        summary: Tool summary.
        content: Tool output content.
        created_at: Unix timestamp.

    Returns:
        Immutable context item.
    """

    tool: str
    summary: str
    content: str
    created_at: int


class ContextWindow:
    """Maintains recent tool outputs for chained ReAct actions.

    Args:
        items: Optional initial context items.

    Returns:
        Mutable context window object.
    """

    def __init__(self, items: list[ContextItem] | None = None):
        self.items = list(items or [])

    def add_tool_result(self, result: ToolResult) -> None:
        """Add a tool result to the context window.

        Args:
            result: ToolResult from an OSS tool.

        Returns:
            None.
        """

        self.items.append(
            ContextItem(
                tool=result.name,
                summary=result.summary,
                content=result.content[:5000],
                created_at=int(time.time()),
            )
        )

    def prune(self, keep: int = 8) -> dict[str, object]:
        """Keep only the newest context observations."""

        keep = max(1, int(keep))
        before = len(self.items)
        self.items = self.items[-keep:]
        return {
            "keep": keep,
            "deleted": max(0, before - len(self.items)),
            "remaining": len(self.items),
        }

    def chained_query(self, prompt: str) -> str:
        """Create a prompt augmented with compact prior observations.

        Args:
            prompt: Original user prompt.

        Returns:
            Prompt plus previous tool observations.
        """

        if not self.items:
            return prompt
        observations = "\n".join(
            f"- {item.tool}: {item.summary}\n{item.content[:1000]}" for item in self.items[-4:]
        )
        return f"{prompt}\n\nPrior tool observations:\n{observations}"

    def serialize(self) -> dict[str, object]:
        """Serialize the context window to JSON-compatible data.

        Args:
            None.

        Returns:
            Dictionary with context items.
        """

        return {"items": [asdict(item) for item in self.items[-20:]]}

    @classmethod
    def deserialize(cls, data: dict[str, object]) -> "ContextWindow":
        """Load a context window from JSON-compatible data.

        Args:
            data: Serialized context window dictionary.

        Returns:
            ContextWindow populated with valid items.
        """

        items = []
        for raw in data.get("items", []):
            if isinstance(raw, dict):
                try:
                    items.append(ContextItem(**raw))
                except TypeError:
                    continue
        return cls(items)
