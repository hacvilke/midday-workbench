from __future__ import annotations

import json

from .config import AgentConfig
from .indexer import search
from .sandbox import ExecutionSandbox


class ToolBox:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.sandbox = ExecutionSandbox(config.workspace_root)

    def workspace_map(self) -> str:
        items = []
        for child in sorted(self.config.workspace_root.iterdir()):
            if child.is_dir():
                items.append(f"- {child.name}/")
        return "\n".join(items)

    def search_workspace(self, query: str, limit: int = 8) -> str:
        results = search(self.config.index_path, query, limit)
        return json.dumps(results, indent=2)

    def read_file(self, path: str, max_chars: int = 6000) -> str:
        target = (self.config.workspace_root / path).resolve()
        if not str(target).startswith(str(self.config.workspace_root)):
            raise ValueError("Path escapes workspace root")
        return target.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    def shell(self, command: str) -> str:
        return self.sandbox.run_read_only(command).output
